# Robot LLM Interface

Embodied AI with Large Language Models for natural language robot control.

## Overview

This package enables the robot to understand and execute complex natural language commands using Large Language Models (LLMs). The system can:

- Parse and understand natural language commands
- Decompose complex multi-step tasks into executable sub-tasks
- Provide human-readable explanations of robot actions
- Ask clarifying questions when commands are ambiguous
- Integrate with the robot's semantic world model

## Features

### Natural Language Understanding
- Support for complex, multi-step commands
- Context-aware command interpretation
- Integration with semantic map for spatial reasoning

### Task Decomposition
- Hierarchical task planning
- Automatic sub-task generation
- Task validation and feasibility checking

### Explanation Generation
- Real-time action explanations
- Reasoning transparency
- Progress updates during execution

### Clarification Dialog
- Ambiguity detection
- Intelligent question generation
- User response parsing

## Supported LLM Providers

### OpenAI (GPT-4, GPT-3.5)
```bash
export OPENAI_API_KEY="your-api-key"
```

### Anthropic (Claude)
```bash
export ANTHROPIC_API_KEY="your-api-key"
```

### Ollama (Local LLMs)
```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama2
ollama pull mistral
```

### LLaMA (Local)
Download and configure a local LLaMA model.

## Installation

### Install Python Dependencies
```bash
cd src/robot_llm_interface
pip3 install -r requirements.txt
```

### Build the Package
```bash
cd ~/robot_ws
colcon build --packages-select robot_llm_interface
source install/setup.bash
```

## Configuration

Edit `config/llm_config.yaml` to configure:
- LLM provider (openai, anthropic, ollama, llama)
- Model parameters (temperature, max_tokens)
- Robot capabilities
- Task planning settings
- Safety settings

## Usage

### Launch LLM Controller
```bash
ros2 launch robot_llm_interface llm_interface.launch.py
```

### Send Commands via Topic
```bash
ros2 topic pub /llm/command std_msgs/String "data: 'Go to the kitchen and find a coffee mug'"
```

### Send Commands via Service
```bash
ros2 service call /llm/execute_command robot_interfaces/ExecuteCommand "{command: 'Navigate to the nearest chair'}"
```

## Example Commands

### Simple Navigation
```
"Go to the kitchen"
"Navigate to the nearest chair"
"Move forward 2 meters"
```

### Object-Based Navigation
```
"Go to the red chair"
"Find the coffee mug"
"Navigate to the table in the living room"
```

### Complex Multi-Step Tasks
```
"Go to the kitchen and bring me a coffee mug"
"Explore the house and create a map"
"Find all chairs in the building and report their locations"
```

### Spatial Reasoning
```
"Go to the room with the most chairs"
"Navigate to the object closest to the door"
"Find the largest open space"
```

## Architecture

```
User Command
    ↓
LLMController (llm_controller.py)
    ↓
Task Decomposition (task_planner.py)
    ↓
Action Execution (Navigation, Perception)
    ↓
Explanation Generation (explanation_generator.py)
    ↓
User Feedback
```

## Topics

### Subscribed
- `/semantic_map` (std_msgs/String) - Semantic map with object locations
- `/robot_pose` (geometry_msgs/PoseStamped) - Current robot position
- `/llm/command` (std_msgs/String) - Natural language commands
- `/llm/clarification_response` (std_msgs/String) - User responses to clarifications

### Published
- `/llm/explanation` (std_msgs/String) - Action explanations
- `/llm/clarification_request` (std_msgs/String) - Clarifying questions
- `/llm/task_status` (std_msgs/String) - Task execution status
- `/navigate_to_object` (geometry_msgs/PoseStamped) - Navigation goals

## Services

- `/llm/execute_command` (robot_interfaces/ExecuteCommand) - Execute a command
- `/llm/get_explanation` (robot_interfaces/GetExplanation) - Get explanation for action
- `/llm/cancel_task` (std_srvs/Trigger) - Cancel current task

## Safety Features

- Confirmation required for critical actions
- Command validation before execution
- Timeout protection
- Emergency stop integration
- Safety distance enforcement

## Performance

- Response time: < 2 seconds for simple commands
- Response time: < 5 seconds for complex commands
- Caching for common commands
- Async processing for non-blocking operation

## Troubleshooting

### LLM API Connection Issues
- Check API keys are set correctly
- Verify network connectivity
- Check API rate limits

### Ollama Connection Issues
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
systemctl restart ollama
```

### Command Not Understood
- Rephrase command more clearly
- Provide more context
- Check semantic map is available

## Development

### Adding New LLM Providers
1. Create provider interface in `llm_providers/`
2. Implement `LLMProvider` base class
3. Add configuration in `llm_config.yaml`
4. Update `llm_controller.py` to support new provider

### Adding New Robot Capabilities
1. Update `robot_capabilities` in config
2. Add capability handlers in `task_planner.py`
3. Update prompt templates

## Testing

```bash
# Run unit tests
pytest src/robot_llm_interface/test/

# Test with simulation
ros2 launch robot_gazebo complete_robot_simulation.launch.py use_llm:=true
```

## References

- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Anthropic Claude Documentation](https://docs.anthropic.com)
- [Ollama Documentation](https://ollama.ai/docs)
- [LLaMA Documentation](https://github.com/facebookresearch/llama)

## License

MIT
