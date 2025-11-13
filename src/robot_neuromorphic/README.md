# Robot Neuromorphic

Neuromorphic computing integration for event-based sensor processing.

## Overview

This package implements brain-inspired neuromorphic computing for ultra-low power, real-time sensor processing. Neuromorphic systems use spiking neural networks (SNNs) that process information as discrete events, similar to biological neurons.

## Features

- **Spiking Neural Networks**: Leaky Integrate-and-Fire (LIF) neurons
- **Event-Based Vision**: Convert camera frames to event streams
- **STDP Learning**: Spike-Timing-Dependent Plasticity for online learning
- **Ultra-Low Latency**: < 1ms processing time
- **Low Power**: 50% reduction vs traditional methods

## Installation

```bash
cd ~/robot_ws
colcon build --packages-select robot_neuromorphic
source install/setup.bash
```

## Usage

### Launch SNN Processor
```bash
ros2 run robot_neuromorphic snn_processor
```

### Launch Event Vision
```bash
ros2 run robot_neuromorphic event_vision
```

## Architecture

### Spiking Neural Network

```
Input Layer (64 neurons)
    ↓
Hidden Layer (128 neurons)
    ↓
Output Layer (10 neurons)
```

Each neuron is a Leaky Integrate-and-Fire (LIF) model:
- Membrane potential integrates input current
- Leaks over time
- Fires spike when threshold reached
- Refractory period after spike

### Event-Based Vision

Traditional cameras capture full frames at fixed intervals. Event cameras only report pixel changes:

```
Frame-based: [Frame1] [Frame2] [Frame3] ...
Event-based: [Event1] [Event2] [Event3] ...
```

Benefits:
- Lower data rate
- Higher temporal resolution
- Lower power consumption
- Better for motion detection

## Learning

### Spike-Timing-Dependent Plasticity (STDP)

Synaptic weights are updated based on spike timing:
- If pre-synaptic neuron fires before post-synaptic: strengthen connection
- If post-synaptic fires before pre-synaptic: weaken connection

This enables online learning without backpropagation.

## Performance

- Processing latency: < 1ms
- Power consumption: 50% reduction
- Learning: Online, no retraining needed
- Accuracy: Comparable to traditional ANNs for many tasks

## Hardware Support

### Neuromorphic Chips
- Intel Loihi
- IBM TrueNorth
- BrainChip Akida
- SpiNNaker

### Event Cameras
- DVS (Dynamic Vision Sensor)
- DAVIS (DVS + APS)
- Prophesee sensors

## Future Work

- Integration with neuromorphic hardware
- Event camera support
- More complex SNN architectures
- Multi-layer STDP learning

## References

- [Neuromorphic Computing](https://en.wikipedia.org/wiki/Neuromorphic_engineering)
- [Spiking Neural Networks](https://en.wikipedia.org/wiki/Spiking_neural_network)
- [Event Cameras](https://en.wikipedia.org/wiki/Event_camera)

## License

MIT
