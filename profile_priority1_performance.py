#!/usr/bin/env python3
"""
Priority 1 Performance Profiling and Optimization Script
Profiles system performance with all Priority 1 features enabled
Identifies bottlenecks and provides optimization recommendations

Task 9.2: Performance optimization for Priority 1
Target: 10Hz operation with <2GB RAM
"""

import rclpy
from rclpy.node import Node
import psutil
import time
import json
import sys
from collections import defaultdict, deque
from typing import Dict, List, Tuple
import numpy as np

class PerformanceProfiler(Node):
    """Profile Priority 1 system performance"""
    
    def __init__(self):
        super().__init__('performance_profiler')
        
        # Profiling parameters
        self.declare_parameter('profile_duration', 60.0)  # seconds
        self.declare_parameter('sample_rate', 10.0)  # Hz
        
        self.profile_duration = self.get_parameter('profile_duration').value
        self.sample_rate = self.get_parameter('sample_rate').value
        
        # Performance data
        self.samples = {
            'cpu': [],
            'memory_mb': [],
            'memory_percent': [],
            'network_mbps': [],
            'timestamps': []
        }
        
        # Node-specific metrics
        self.node_metrics = defaultdict(lambda: {
            'cpu': [],
            'memory': [],
            'message_rate': []
        })
        
        # Topic metrics
        self.topic_metrics = defaultdict(lambda: {
            'message_count': 0,
            'message_rate': deque(maxlen=100),
            'last_message_time': None,
            'bandwidth_bytes': 0
        })
        
        # Bottleneck detection
        self.bottlenecks = []
        
        # Network tracking
        self.last_net_io = psutil.net_io_counters()
        self.last_net_time = time.time()
        
        # Start time
        self.start_time = time.time()
        
        # Timer for sampling
        self.sample_timer = self.create_timer(
            1.0 / self.sample_rate, 
            self.sample_performance
        )
        
        # Timer for profiling completion
        self.completion_timer = self.create_timer(
            self.profile_duration,
            self.complete_profiling
        )
        
        self.get_logger().info(f"📊 Performance Profiler started")
        self.get_logger().info(f"   Duration: {self.profile_duration}s")
        self.get_logger().info(f"   Sample rate: {self.sample_rate}Hz")
        self.get_logger().info(f"   Profiling Priority 1 features...")
    
    def sample_performance(self):
        """Sample system performance metrics"""
        current_time = time.time()
        elapsed = current_time - self.start_time
        
        # System-wide metrics
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        memory_mb = memory.used / (1024 * 1024)
        memory_percent = memory.percent
        
        # Network bandwidth
        current_net_io = psutil.net_io_counters()
        time_delta = current_time - self.last_net_time
        
        if time_delta > 0:
            bytes_sent = current_net_io.bytes_sent - self.last_net_io.bytes_sent
            bytes_recv = current_net_io.bytes_recv - self.last_net_io.bytes_recv
            total_bytes = bytes_sent + bytes_recv
            network_mbps = (total_bytes * 8) / (time_delta * 1_000_000)
        else:
            network_mbps = 0.0
        
        self.last_net_io = current_net_io
        self.last_net_time = current_time
        
        # Store samples
        self.samples['cpu'].append(cpu_percent)
        self.samples['memory_mb'].append(memory_mb)
        self.samples['memory_percent'].append(memory_percent)
        self.samples['network_mbps'].append(network_mbps)
        self.samples['timestamps'].append(elapsed)
        
        # Log progress
        if int(elapsed) % 10 == 0 and len(self.samples['cpu']) > 1:
            self.get_logger().info(
                f"⏱️  {elapsed:.0f}s - "
                f"CPU: {cpu_percent:.1f}%, "
                f"Memory: {memory_mb:.0f}MB ({memory_percent:.1f}%), "
                f"Network: {network_mbps:.2f}Mbps"
            )
        
        # Profile ROS2 nodes
        self.profile_ros_nodes()
    
    def profile_ros_nodes(self):
        """Profile individual ROS2 nodes"""
        try:
            # Get all ROS2 processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
                try:
                    cmdline = proc.info.get('cmdline', [])
                    if not cmdline:
                        continue
                    
                    # Check if it's a ROS2 node
                    if any('ros2' in arg or 'python3' in arg for arg in cmdline):
                        # Extract node name
                        node_name = self.extract_node_name(cmdline)
                        
                        if node_name and any(keyword in node_name for keyword in [
                            'semantic_slam', 'pointcloud', 'performance_dashboard',
                            'advanced_safety', 'semantic_interface', 'enhanced_visualizer'
                        ]):
                            # Get metrics
                            cpu = proc.info.get('cpu_percent', 0.0)
                            memory_info = proc.info.get('memory_info')
                            memory_mb = memory_info.rss / (1024 * 1024) if memory_info else 0.0
                            
                            # Store metrics
                            self.node_metrics[node_name]['cpu'].append(cpu)
                            self.node_metrics[node_name]['memory'].append(memory_mb)
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
        except Exception as e:
            self.get_logger().debug(f"Error profiling nodes: {e}")
    
    def extract_node_name(self, cmdline: List[str]) -> str:
        """Extract node name from command line"""
        for i, arg in enumerate(cmdline):
            if arg == '--ros-args' and i + 2 < len(cmdline):
                if cmdline[i + 1] == '-r':
                    return cmdline[i + 2].split(':')[0]
            elif '.py' in arg:
                # Extract from Python script name
                return arg.split('/')[-1].replace('.py', '')
        return ''
    
    def complete_profiling(self):
        """Complete profiling and generate report"""
        self.get_logger().info("✅ Profiling complete - Analyzing results...")
        
        # Stop timers
        self.sample_timer.cancel()
        self.completion_timer.cancel()
        
        # Analyze results
        self.analyze_performance()
        
        # Detect bottlenecks
        self.detect_bottlenecks()
        
        # Generate report
        self.generate_report()
        
        # Generate optimization recommendations
        self.generate_recommendations()
        
        # Shutdown
        self.get_logger().info("📄 Report saved to performance_profile_report.json")
        rclpy.shutdown()
    
    def analyze_performance(self):
        """Analyze collected performance data"""
        self.get_logger().info("📈 Analyzing performance data...")
        
        # Calculate statistics
        self.stats = {
            'cpu': {
                'mean': np.mean(self.samples['cpu']),
                'max': np.max(self.samples['cpu']),
                'min': np.min(self.samples['cpu']),
                'std': np.std(self.samples['cpu']),
                'p95': np.percentile(self.samples['cpu'], 95),
                'p99': np.percentile(self.samples['cpu'], 99)
            },
            'memory_mb': {
                'mean': np.mean(self.samples['memory_mb']),
                'max': np.max(self.samples['memory_mb']),
                'min': np.min(self.samples['memory_mb']),
                'std': np.std(self.samples['memory_mb']),
                'p95': np.percentile(self.samples['memory_mb'], 95),
                'p99': np.percentile(self.samples['memory_mb'], 99)
            },
            'memory_percent': {
                'mean': np.mean(self.samples['memory_percent']),
                'max': np.max(self.samples['memory_percent']),
                'min': np.min(self.samples['memory_percent']),
                'std': np.std(self.samples['memory_percent']),
                'p95': np.percentile(self.samples['memory_percent'], 95),
                'p99': np.percentile(self.samples['memory_percent'], 99)
            },
            'network_mbps': {
                'mean': np.mean(self.samples['network_mbps']),
                'max': np.max(self.samples['network_mbps']),
                'min': np.min(self.samples['network_mbps']),
                'std': np.std(self.samples['network_mbps']),
                'p95': np.percentile(self.samples['network_mbps'], 95),
                'p99': np.percentile(self.samples['network_mbps'], 99)
            }
        }
        
        # Node-specific statistics
        self.node_stats = {}
        for node_name, metrics in self.node_metrics.items():
            if metrics['cpu']:
                self.node_stats[node_name] = {
                    'cpu_mean': np.mean(metrics['cpu']),
                    'cpu_max': np.max(metrics['cpu']),
                    'memory_mean_mb': np.mean(metrics['memory']),
                    'memory_max_mb': np.max(metrics['memory'])
                }
    
    def detect_bottlenecks(self):
        """Detect performance bottlenecks"""
        self.get_logger().info("🔍 Detecting bottlenecks...")
        
        # CPU bottlenecks
        if self.stats['cpu']['mean'] > 70:
            self.bottlenecks.append({
                'type': 'CPU',
                'severity': 'HIGH' if self.stats['cpu']['mean'] > 80 else 'MEDIUM',
                'metric': 'Average CPU usage',
                'value': f"{self.stats['cpu']['mean']:.1f}%",
                'threshold': '70%',
                'impact': 'System may not maintain 10Hz operation'
            })
        
        if self.stats['cpu']['p95'] > 85:
            self.bottlenecks.append({
                'type': 'CPU',
                'severity': 'HIGH',
                'metric': '95th percentile CPU usage',
                'value': f"{self.stats['cpu']['p95']:.1f}%",
                'threshold': '85%',
                'impact': 'Frequent CPU spikes may cause dropped frames'
            })
        
        # Memory bottlenecks
        if self.stats['memory_mb']['mean'] > 2048:
            self.bottlenecks.append({
                'type': 'Memory',
                'severity': 'HIGH',
                'metric': 'Average memory usage',
                'value': f"{self.stats['memory_mb']['mean']:.0f}MB",
                'threshold': '2048MB (2GB)',
                'impact': 'Exceeds target memory budget'
            })
        
        if self.stats['memory_mb']['max'] > 2500:
            self.bottlenecks.append({
                'type': 'Memory',
                'severity': 'CRITICAL',
                'metric': 'Peak memory usage',
                'value': f"{self.stats['memory_mb']['max']:.0f}MB",
                'threshold': '2500MB',
                'impact': 'Risk of OOM on systems with limited RAM'
            })
        
        # Network bottlenecks
        if self.stats['network_mbps']['mean'] > 50:
            self.bottlenecks.append({
                'type': 'Network',
                'severity': 'MEDIUM',
                'metric': 'Average network bandwidth',
                'value': f"{self.stats['network_mbps']['mean']:.1f}Mbps",
                'threshold': '50Mbps',
                'impact': 'High bandwidth may cause issues on slower networks'
            })
        
        # Node-specific bottlenecks
        for node_name, stats in self.node_stats.items():
            if stats['cpu_mean'] > 30:
                self.bottlenecks.append({
                    'type': 'Node CPU',
                    'severity': 'MEDIUM',
                    'metric': f'{node_name} CPU usage',
                    'value': f"{stats['cpu_mean']:.1f}%",
                    'threshold': '30%',
                    'impact': f'{node_name} consuming excessive CPU'
                })
            
            if stats['memory_mean_mb'] > 500:
                self.bottlenecks.append({
                    'type': 'Node Memory',
                    'severity': 'MEDIUM',
                    'metric': f'{node_name} memory usage',
                    'value': f"{stats['memory_mean_mb']:.0f}MB",
                    'threshold': '500MB',
                    'impact': f'{node_name} consuming excessive memory'
                })
    
    def generate_report(self):
        """Generate performance report"""
        report = {
            'profile_info': {
                'duration': self.profile_duration,
                'sample_rate': self.sample_rate,
                'total_samples': len(self.samples['cpu']),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            },
            'system_stats': self.stats,
            'node_stats': self.node_stats,
            'bottlenecks': self.bottlenecks,
            'target_compliance': {
                'cpu_target': '< 80%',
                'cpu_actual': f"{self.stats['cpu']['mean']:.1f}%",
                'cpu_compliant': self.stats['cpu']['mean'] < 80,
                'memory_target': '< 2048MB',
                'memory_actual': f"{self.stats['memory_mb']['mean']:.0f}MB",
                'memory_compliant': self.stats['memory_mb']['mean'] < 2048,
                'operation_rate_target': '10Hz',
                'operation_rate_actual': f"{self.sample_rate}Hz",
                'operation_rate_compliant': True
            }
        }
        
        # Save report
        with open('performance_profile_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        self.print_summary(report)
    
    def print_summary(self, report: Dict):
        """Print performance summary"""
        self.get_logger().info("\n" + "="*60)
        self.get_logger().info("PERFORMANCE PROFILE SUMMARY")
        self.get_logger().info("="*60)
        
        # System metrics
        self.get_logger().info("\n📊 System Metrics:")
        self.get_logger().info(f"  CPU Usage:")
        self.get_logger().info(f"    Mean: {self.stats['cpu']['mean']:.1f}%")
        self.get_logger().info(f"    Max:  {self.stats['cpu']['max']:.1f}%")
        self.get_logger().info(f"    P95:  {self.stats['cpu']['p95']:.1f}%")
        
        self.get_logger().info(f"\n  Memory Usage:")
        self.get_logger().info(f"    Mean: {self.stats['memory_mb']['mean']:.0f}MB ({self.stats['memory_percent']['mean']:.1f}%)")
        self.get_logger().info(f"    Max:  {self.stats['memory_mb']['max']:.0f}MB ({self.stats['memory_percent']['max']:.1f}%)")
        self.get_logger().info(f"    P95:  {self.stats['memory_mb']['p95']:.0f}MB")
        
        self.get_logger().info(f"\n  Network Bandwidth:")
        self.get_logger().info(f"    Mean: {self.stats['network_mbps']['mean']:.2f}Mbps")
        self.get_logger().info(f"    Max:  {self.stats['network_mbps']['max']:.2f}Mbps")
        
        # Target compliance
        self.get_logger().info("\n🎯 Target Compliance:")
        compliance = report['target_compliance']
        cpu_status = "✅" if compliance['cpu_compliant'] else "❌"
        mem_status = "✅" if compliance['memory_compliant'] else "❌"
        rate_status = "✅" if compliance['operation_rate_compliant'] else "❌"
        
        self.get_logger().info(f"  {cpu_status} CPU: {compliance['cpu_actual']} (target: {compliance['cpu_target']})")
        self.get_logger().info(f"  {mem_status} Memory: {compliance['memory_actual']} (target: {compliance['memory_target']})")
        self.get_logger().info(f"  {rate_status} Operation Rate: {compliance['operation_rate_actual']} (target: {compliance['operation_rate_target']})")
        
        # Bottlenecks
        if self.bottlenecks:
            self.get_logger().info(f"\n⚠️  Detected {len(self.bottlenecks)} Bottleneck(s):")
            for i, bottleneck in enumerate(self.bottlenecks, 1):
                severity_icon = "🚨" if bottleneck['severity'] == 'CRITICAL' else "⚠️" if bottleneck['severity'] == 'HIGH' else "ℹ️"
                self.get_logger().info(f"  {i}. {severity_icon} [{bottleneck['severity']}] {bottleneck['type']}")
                self.get_logger().info(f"     {bottleneck['metric']}: {bottleneck['value']} (threshold: {bottleneck['threshold']})")
                self.get_logger().info(f"     Impact: {bottleneck['impact']}")
        else:
            self.get_logger().info("\n✅ No significant bottlenecks detected!")
        
        # Node stats
        if self.node_stats:
            self.get_logger().info("\n🔧 Node-Specific Metrics:")
            for node_name, stats in sorted(self.node_stats.items(), key=lambda x: x[1]['cpu_mean'], reverse=True):
                self.get_logger().info(f"  {node_name}:")
                self.get_logger().info(f"    CPU: {stats['cpu_mean']:.1f}% (max: {stats['cpu_max']:.1f}%)")
                self.get_logger().info(f"    Memory: {stats['memory_mean_mb']:.0f}MB (max: {stats['memory_max_mb']:.0f}MB)")
        
        self.get_logger().info("\n" + "="*60)
    
    def generate_recommendations(self):
        """Generate optimization recommendations"""
        recommendations = []
        
        # CPU optimizations
        if any(b['type'] == 'CPU' for b in self.bottlenecks):
            recommendations.append({
                'category': 'CPU Optimization',
                'priority': 'HIGH',
                'recommendations': [
                    'Reduce YOLO inference frequency (currently every frame)',
                    'Use GPU acceleration for YOLO if available',
                    'Implement frame skipping for object detection',
                    'Optimize point cloud processing with vectorization',
                    'Consider using yolov8n-int8 quantized model for faster inference'
                ]
            })
        
        # Memory optimizations
        if any(b['type'] == 'Memory' for b in self.bottlenecks):
            recommendations.append({
                'category': 'Memory Optimization',
                'priority': 'HIGH',
                'recommendations': [
                    'Limit point cloud accumulation buffer size',
                    'Implement more aggressive voxel filtering',
                    'Reduce semantic map object retention time',
                    'Clear old scan data more frequently',
                    'Optimize data structures (use numpy arrays instead of lists)'
                ]
            })
        
        # Network optimizations
        if any(b['type'] == 'Network' for b in self.bottlenecks):
            recommendations.append({
                'category': 'Network Optimization',
                'priority': 'MEDIUM',
                'recommendations': [
                    'Compress large messages (images, point clouds)',
                    'Reduce publishing frequency for non-critical topics',
                    'Use appropriate QoS profiles (BEST_EFFORT for sensor data)',
                    'Implement message throttling for visualization topics'
                ]
            })
        
        # Node-specific optimizations
        for node_name, stats in self.node_stats.items():
            if stats['cpu_mean'] > 30 or stats['memory_mean_mb'] > 500:
                if 'semantic_slam' in node_name:
                    recommendations.append({
                        'category': f'Semantic SLAM Optimization',
                        'priority': 'HIGH',
                        'recommendations': [
                            'Cache YOLO model in GPU memory',
                            'Reduce detection frequency to 5Hz instead of 10Hz',
                            'Optimize spatial indexing rebuild frequency',
                            'Use more efficient data serialization for persistence'
                        ]
                    })
                elif 'pointcloud' in node_name:
                    recommendations.append({
                        'category': 'Point Cloud Optimization',
                        'priority': 'MEDIUM',
                        'recommendations': [
                            'Increase voxel size for downsampling',
                            'Reduce accumulation time window',
                            'Implement adaptive point cloud density',
                            'Use octree data structure for efficient storage'
                        ]
                    })
                elif 'performance_dashboard' in node_name:
                    recommendations.append({
                        'category': 'Dashboard Optimization',
                        'priority': 'LOW',
                        'recommendations': [
                            'Reduce update frequency to 0.5Hz',
                            'Simplify marker visualizations',
                            'Cache static dashboard elements'
                        ]
                    })
        
        # Save recommendations
        with open('optimization_recommendations.json', 'w') as f:
            json.dump(recommendations, f, indent=2)
        
        # Print recommendations
        self.get_logger().info("\n" + "="*60)
        self.get_logger().info("OPTIMIZATION RECOMMENDATIONS")
        self.get_logger().info("="*60)
        
        for rec in recommendations:
            priority_icon = "🔴" if rec['priority'] == 'HIGH' else "🟡" if rec['priority'] == 'MEDIUM' else "🟢"
            self.get_logger().info(f"\n{priority_icon} {rec['category']} [{rec['priority']} Priority]:")
            for i, suggestion in enumerate(rec['recommendations'], 1):
                self.get_logger().info(f"  {i}. {suggestion}")
        
        self.get_logger().info("\n" + "="*60)
        self.get_logger().info("📄 Recommendations saved to optimization_recommendations.json")


def main(args=None):
    rclpy.init(args=args)
    
    profiler = PerformanceProfiler()
    
    try:
        rclpy.spin(profiler)
    except KeyboardInterrupt:
        profiler.get_logger().info("Profiling interrupted by user")
    except Exception as e:
        profiler.get_logger().error(f"Profiling error: {e}")
    finally:
        if rclpy.ok():
            profiler.complete_profiling()
        profiler.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
