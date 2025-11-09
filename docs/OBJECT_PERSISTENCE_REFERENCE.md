# Object Persistence Quick Reference

## Overview
Robust object persistence with timeout, decay, and disk storage.

---

## Key Features

| Feature | Value | Description |
|---------|-------|-------------|
| **Timeout** | 5 minutes | Objects removed after this time |
| **Decay Rate** | 5% per minute | Confidence decay when unseen |
| **Min Confidence** | 30% | Objects removed below this |
| **Merge Distance** | 1.0m | Objects merged within this distance |
| **Save Frequency** | 30 seconds | Automatic save interval |
| **Cleanup Frequency** | 60 seconds | Automatic cleanup interval |

---

## Configuration

### Default Parameters
```bash
persistence_file: semantic_map_persistent.pkl
object_timeout_seconds: 300.0
confidence_decay_rate: 0.95
min_confidence_threshold: 0.3
merge_distance_threshold: 1.0
```

### Custom Configuration
```bash
ros2 run robot_semantic_slam semantic_slam_node \
    --ros-args \
    -p persistence_file:=/tmp/my_map.pkl \
    -p object_timeout_seconds:=600.0 \
    -p confidence_decay_rate:=0.90 \
    -p min_confidence_threshold:=0.2 \
    -p merge_distance_threshold:=1.5
```

---

## Object Lifecycle

```
┌─────────────────────────────────────────────────────────┐
│                   Object Lifecycle                      │
└─────────────────────────────────────────────────────────┘

1. DETECTION
   ↓
   New object created with:
   - Initial position
   - Confidence from YOLO
   - Detection count = 1
   - Timestamps set

2. RE-DETECTION (within merge distance)
   ↓
   Object updated with:
   - Weighted average position
   - Max confidence
   - Detection count++
   - Last seen timestamp updated

3. NOT SEEN (1+ minutes)
   ↓
   Confidence decays:
   - 5% per minute
   - Applied during cleanup

4. TIMEOUT (5 minutes) OR LOW CONFIDENCE (<30%)
   ↓
   Object removed from map
   - Logged for debugging
   - Removed from persistence file
```

---

## Confidence Decay

### Decay Formula
```
confidence_new = confidence_old * (decay_rate ^ minutes_unseen)
```

### Decay Table
| Time | Confidence (from 1.0) | Confidence (from 0.5) |
|------|----------------------|----------------------|
| 0 min | 1.00 | 0.50 |
| 1 min | 0.95 | 0.48 |
| 2 min | 0.90 | 0.45 |
| 5 min | 0.77 | 0.39 |
| 10 min | 0.60 | 0.30 |
| 15 min | 0.46 | 0.23 (removed) |

---

## Object Merging

### Weighted Average Formula
```
new_x = (old_x * old_detections + new_x * 1) / (old_detections + 1)
new_y = (old_y * old_detections + new_y * 1) / (old_detections + 1)
```

### Example
```
Existing: 5 detections at (2.0, 1.0)
New: 1 detection at (2.3, 1.2)

Result: (2.05, 1.03) with 6 detections
```

### Merge Conditions
1. Same object class
2. Within merge distance (1.0m default)
3. Closest match selected

---

## Persistence File

### Location
```bash
# Default
./semantic_map_persistent.pkl

# Check if exists
ls -lh semantic_map_persistent.pkl

# View contents
python3 -c "import pickle; print(pickle.load(open('semantic_map_persistent.pkl', 'rb')))"
```

### File Structure
```python
{
    'semantic_map': {
        'object_id': {
            'class': str,
            'x': float,
            'y': float,
            'confidence': float,
            'last_seen': float,
            'detections': int,
            'created_at': float
        }
    },
    'object_counter': int,
    'saved_at': float
}
```

### Save Schedule
- **Automatic**: Every 30 seconds
- **Shutdown**: On node termination
- **Manual**: Call `save_semantic_map()`

---

## Monitoring

### Check Object Count
```bash
ros2 topic echo /semantic_map --once | grep -c "class"
```

### Monitor Cleanup
```bash
# Watch logs for cleanup messages
ros2 node info /semantic_slam_node
```

### Check Persistence File Age
```bash
stat semantic_map_persistent.pkl
```

---

## Troubleshooting

### Objects Disappearing Too Fast
```bash
# Increase timeout to 10 minutes
-p object_timeout_seconds:=600.0

# Reduce decay rate (3% per minute)
-p confidence_decay_rate:=0.97
```

### Too Many Old Objects
```bash
# Decrease timeout to 3 minutes
-p object_timeout_seconds:=180.0

# Increase decay rate (10% per minute)
-p confidence_decay_rate:=0.90
```

### Objects Not Merging
```bash
# Increase merge distance to 2 meters
-p merge_distance_threshold:=2.0
```

### Persistence File Not Created
- Wait for first save (30 seconds)
- Check write permissions
- Verify disk space

---

## Testing

### Unit Tests
```bash
cd src/robot_semantic_slam
python3 -m pytest test/test_object_persistence.py -v
```

### Integration Test
```bash
python3 test_task_1_3_validation.py
```

### Manual Test
```bash
# 1. Launch system
ros2 launch robot_semantic_slam cutting_edge_features.launch.py

# 2. Detect some objects
# (move robot around)

# 3. Check persistence file
ls -lh semantic_map_persistent.pkl

# 4. Restart node
# (Ctrl+C and relaunch)

# 5. Verify objects loaded
ros2 topic echo /semantic_map --once
```

---

## Performance

### Memory
- Per object: ~200 bytes
- 1000 objects: ~200 KB

### CPU
- Cleanup: <1% (every 60s)
- Save: <1% (every 30s)
- Merge: <0.1% per detection

### Disk
- File size: 100-500 KB
- Write frequency: Every 30s
- I/O: ~1-2 MB/minute

---

## Best Practices

1. **Timeout**: Set based on environment size
   - Small room: 3-5 minutes
   - Large building: 10-15 minutes

2. **Decay Rate**: Adjust for object stability
   - Static objects: 0.98 (2% decay)
   - Dynamic environment: 0.90 (10% decay)

3. **Merge Distance**: Match sensor accuracy
   - High accuracy: 0.5m
   - Low accuracy: 2.0m

4. **Backup**: Periodically backup persistence file
   ```bash
   cp semantic_map_persistent.pkl backup_$(date +%Y%m%d).pkl
   ```

---

## Related Files

- Implementation: `src/robot_semantic_slam/robot_semantic_slam/semantic_slam_node.py`
- Unit Tests: `src/robot_semantic_slam/test/test_object_persistence.py`
- Integration Test: `test_task_1_3_validation.py`
- Documentation: `docs/TASK_1_3_VERIFICATION.md`
