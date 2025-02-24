import os
import json
import glob
import shutil
import importlib
import yaml
import uuid
from pathlib import Path
from dotenv import load_dotenv
from inspect import signature, Parameter
load_dotenv()

class Config():
    def __init__(self, agent_name=None):
        # General Configuration
        self.AGENT_NAME = agent_name if agent_name is not None else os.getenv("AGENT_NAME", "default")
        self.AGENTS = glob.glob(os.path.join("memories", "*.yaml"))
        # Goal Configuation
        self.OBJECTIVE = os.getenv("OBJECTIVE", "Solve world hunger")
        self.INITIAL_TASK = os.getenv("INITIAL_TASK", "Develop a task list")
        
        # AI Configuration
        self.AI_PROVIDER = os.getenv("AI_PROVIDER", "openai").lower()

        # AI_PROVIDER_URI is only needed for custom AI providers such as Oobabooga Text Generation Web UI
        self.AI_PROVIDER_URI = os.getenv("AI_PROVIDER_URI", "http://127.0.0.1:7860")
        self.MODEL_PATH = os.getenv("MODEL_PATH")

        # ChatGPT Configuration
        self.CHATGPT_USERNAME = os.getenv("CHATGPT_USERNAME")
        self.CHATGPT_PASSWORD = os.getenv("CHATGPT_PASSWORD")

        self.COMMANDS_ENABLED = os.getenv("COMMANDS_ENABLED", "true").lower()
        self.WORKING_DIRECTORY = os.getenv("WORKING_DIRECTORY", "WORKSPACE")
        if not os.path.exists(self.WORKING_DIRECTORY):
            os.makedirs(self.WORKING_DIRECTORY)
        
        # Memory Settings
        self.NO_MEMORY = os.getenv("NO_MEMORY", "false").lower()
        self.USE_LONG_TERM_MEMORY_ONLY = os.getenv("USE_LONG_TERM_MEMORY_ONLY", "false").lower()

        # Model configuration
        self.AI_MODEL = os.getenv("AI_MODEL", "gpt-3.5-turbo").lower()
        self.AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", 0.4))
        self.MAX_TOKENS = os.getenv("MAX_TOKENS", 2000)
        
        # Extensions Configuration

        # OpenAI
        self.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

        # Bard
        self.BARD_TOKEN = os.getenv("BARD_TOKEN")

        # Huggingface
        self.HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
        self.HUGGINGFACE_AUDIO_TO_TEXT_MODEL = os.getenv("HUGGINGFACE_AUDIO_TO_TEXT_MODEL", "facebook/wav2vec2-large-960h-lv60-self")
        
        # Selenium
        self.SELENIUM_WEB_BROWSER = os.getenv("SELENIUM_WEB_BROWSER", "chrome").lower()

        # Twitter
        self.TW_CONSUMER_KEY = os.getenv("TW_CONSUMER_KEY")
        self.TW_CONSUMER_SECRET = os.getenv("TW_CONSUMER_SECRET")
        self.TW_ACCESS_TOKEN = os.getenv("TW_ACCESS_TOKEN")
        self.TW_ACCESS_TOKEN_SECRET = os.getenv("TW_ACCESS_TOKEN_SECRET")

        # Github
        self.GITHUB_API_KEY = os.getenv("GITHUB_API_KEY")
        self.GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

        # Sendgrid
        self.SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
        self.SENDGRID_EMAIL = os.getenv("SENDGRID_EMAIL")

        # Microsft 365
        self.MICROSOFT_365_CLIENT_ID = os.getenv("MICROSOFT_365_CLIENT_ID")
        self.MICROSOFT_365_CLIENT_SECRET = os.getenv("MICROSOFT_365_CLIENT_SECRET")
        self.MICROSOFT_365_REDIRECT_URI = os.getenv("MICROSOFT_365_REDIRECT_URI")

        # Voice (Choose one: ElevenLabs, Brian, Mac OS)
        # Elevenlabs
        self.ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
        self.ELEVENLABS_VOICE = os.getenv("ELEVENLABS_VOICE", "Josh")
        # Mac OS TTS
        self.USE_MAC_OS_TTS = os.getenv("USE_MAC_OS_TTS", "false").lower()

        # Brian TTS
        self.USE_BRIAN_TTS = os.getenv("USE_BRIAN_TTS", "true").lower()
        
        # Yaml Memory
        self.memory_folder = "agents"
        self.memory_file = f"{self.memory_folder}/{self.AGENT_NAME}.yaml"
        memory_file_path = Path(self.memory_file)
        memory_file_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory = self.load_memory()
        self.agent_instances = {}
        self.commands = {}
        if not os.path.exists(f"model-prompts/{self.AI_MODEL}"):
            self.AI_MODEL = "default"
        execute_file = f"model-prompts/{self.AI_MODEL}/execute.txt"
        task_file = f"model-prompts/{self.AI_MODEL}/task.txt"
        priority_file = f"model-prompts/{self.AI_MODEL}/priority.txt"
        
        with open(execute_file, "r") as f:
            self.EXECUTION_PROMPT = f.read()
        with open(task_file, "r") as f:
            self.TASK_PROMPT = f.read()
        with open(priority_file, "r") as f:
            self.PRIORITY_PROMPT = f.read()

    def get_providers(self):
        providers = []
        for provider in glob.glob("provider/*.py"):
            if provider != "provider/__init__.py":
                providers.append(provider.replace("provider/", "").replace(".py", ""))
        return providers

    def create_agent_folder(self, agent_name):
        agent_folder = f"agents/{agent_name}"
        if not os.path.exists("agents"):
            os.makedirs("agents")
        if not os.path.exists(agent_folder):
            os.makedirs(agent_folder)
        return agent_folder

    def load_command_files(self):
        command_files = glob.glob("commands/*.py")
        return command_files

    def get_command_params(self, func):
        params = {}
        sig = signature(func)
        for name, param in sig.parameters.items():
            if param.default == Parameter.empty:
                params[name] = None
            else:
                params[name] = param.default
        return params

    def load_commands(self):
        commands = []
        command_files = self.load_command_files()
        for command_file in command_files:    
            module_name = os.path.splitext(os.path.basename(command_file))[0]
            module = importlib.import_module(f"commands.{module_name}")
            command_class = getattr(module, module_name)()
            if hasattr(command_class, 'commands'):
                for command_name, command_function in command_class.commands.items():
                    params = self.get_command_params(command_function)
                    commands.append((command_name, command_function.__name__, params))
        return commands

    def create_agent_config_file(self, agent_folder):
        agent_config_file = os.path.join(agent_folder, "config.json")
        if not os.path.exists(agent_config_file):
            with open(agent_config_file, "w") as f:
                f.write(json.dumps({"commands": {command_name: "true" for command_name, _, _ in self.commands}}))
        return agent_config_file

    def load_agent_config(self, agent_name):
        try:
            with open(os.path.join("agents", agent_name, "config.json")) as agent_config:
                try:
                    agent_config_data = json.load(agent_config)
                except json.JSONDecodeError:
                    agent_config_data = {}
                    # Populate the agent_config with all commands enabled
                    agent_config_data["commands"] = {command_name: "true" for command_name, _, _ in self.load_commands(agent_name)}
                    # Save the updated agent_config to the file
                    with open(os.path.join("agents", agent_name, "config.json"), "w") as agent_config_file:
                        json.dump(agent_config_data, agent_config_file)
        except:
            # Add all commands to agent/{agent_name}/config.json in this format {"command_name": "true"}
            agent_config_file = os.path.join("agents", agent_name, "config.json")
            with open(agent_config_file, "w") as f:
                f.write(json.dumps({"commands": {command_name: "true" for command_name, _, _ in self.commands}}))
        return agent_config_data
    
    def create_agent_yaml_file(self, agent_name):
        memories_dir = "agents"
        if not os.path.exists(memories_dir):
            os.makedirs(memories_dir)
        i = 0
        agent_file = f"{agent_name}.yaml"
        while os.path.exists(os.path.join(memories_dir, agent_file)):
            i += 1
            agent_file = f"{agent_name}_{i}.yaml"
        with open(os.path.join(memories_dir, agent_file), "w") as f:
            f.write("")
        return agent_file
    
    def write_agent_config(self, agent_config, config_data):
        with open(agent_config, "w") as f:
            json.dump(config_data, f)

    def add_agent(self, agent_name):
        agent_file = self.create_agent_yaml_file(agent_name)
        agent_folder = self.create_agent_folder(agent_name)
        agent_config = self.create_agent_config_file(agent_folder)
        commands_list = self.load_commands()
        command_dict = {}
        for command in commands_list:
            friendly_name, command_name, command_args = command
            command_dict[friendly_name] = True
        self.write_agent_config(agent_config, {"commands": command_dict})
        return {"agent_file": agent_file}

    def rename_agent(self, agent_name, new_name):
        agent_file = f"agents/{agent_name}.yaml"
        agent_folder = f"agents/{agent_name}/"
        agent_file = os.path.abspath(agent_file)
        agent_folder = os.path.abspath(agent_folder)
        if os.path.exists(agent_file):
            os.rename(agent_file, os.path.join("agents", f"{new_name}.yaml"))
        if os.path.exists(agent_folder):
            os.rename(agent_folder, os.path.join("agents", f"{new_name}"))

    def delete_agent(self, agent_name):
        agent_file = f"agents/{agent_name}.yaml"
        agent_folder = f"agents/{agent_name}/"
        agent_file = os.path.abspath(agent_file)
        agent_folder = os.path.abspath(agent_folder)
        try:
            os.remove(agent_file)
        except FileNotFoundError:
            return {"message": f"Agent file {agent_file} not found."}, 404

        if os.path.exists(agent_folder):
            shutil.rmtree(agent_folder)

        return {"message": f"Agent {agent_name} deleted."}, 200

    def get_agents(self):
        memories_dir = "agents"
        if not os.path.exists(memories_dir):
            os.makedirs(memories_dir)
        agents = []
        for file in os.listdir(memories_dir):
            if file.endswith(".yaml"):
                agents.append(file.replace(".yaml", ""))
        output = []
        if not agents:
            # Create a new agent
            self.add_agent("Agent-LLM")
            agents = ["Agent-LLM"]
        for agent in agents:
            try:
                agent_instance = self.agent_instances[agent]
                status = agent_instance.get_status()
            except:
                status = False
            output.append({"name": agent, "status": status})
        return output

    def get_agent_config(self, agent_name):
        agent_file = os.path.abspath(f"agents/{agent_name}/config.json")
        if os.path.exists(agent_file):
            with open(agent_file, "r") as f:
                agent_config = json.load(f)
        else:
            agent_config = {}
        return agent_config

    def get_chat_history(self, agent_name):
        if not os.path.exists(os.path.join("agents", f"{agent_name}.yaml")):
            return ""
        with open(os.path.join("agents", f"{agent_name}.yaml"), "r") as f:
            chat_history = f.read()
        return chat_history

    def wipe_agent_memories(self, agent_name):
        agent_folder = f"agents/{agent_name}/"
        agent_folder = os.path.abspath(agent_folder)
        memories_folder = os.path.join(agent_folder, "memories")
        if os.path.exists(memories_folder):
            shutil.rmtree(memories_folder)

    def update_agent_config(self, agent_name, config):
        with open(os.path.join("agents", agent_name, "config.json"), "w") as agent_config:
            json.dump(config, agent_config)

    def get_task_output(self, agent_name, task_id=None):
        if task_id is None:
            # Get the latest task
            task_id = sorted(os.listdir(os.path.join("agents", agent_name, "tasks")))[-1].replace(".txt", "")
        task_output_file = os.path.join("agents", agent_name, "tasks", f"{task_id}.txt")
        if os.path.exists(task_output_file):
            with open(task_output_file, "r") as f:
                task_output = f.read()
        else:
            task_output = ""
        return task_output
    
    def save_task_output(self, agent_name, task_output, task_id=None):
        if task_id is None:
            task_id = str(uuid.uuid4())
        if not os.path.exists(os.path.join("agents", agent_name, "tasks")):
            os.makedirs(os.path.join("agents", agent_name, "tasks"))
        task_output_file = os.path.join("agents", agent_name, "tasks", f"{task_id}.txt")
        with open(task_output_file, "w") as f:
            f.write(task_output)
    
    def get_chains(self):
        chains = os.listdir("chains")
        chain_data = {}
        for chain in chains:
            chain_steps = os.listdir(os.path.join("chains", chain))
            for step in chain_steps:
                step_number = step.split("-")[0]
                prompt_type = step.split("-")[1]
                with open(os.path.join("chains", chain, step), "r") as f:
                    prompt = f.read()
                if chain not in chain_data:
                    chain_data[chain] = {}
                if step_number not in chain_data[chain]:
                    chain_data[chain][step_number] = {}
                chain_data[chain][step_number][prompt_type] = prompt
        return chain_data

    def get_chain(self, chain_name):
        chain_steps = os.listdir(os.path.join("chains", chain_name))
        chain_data = {}
        for step in chain_steps:
            step_number = step.split("-")[0]
            prompt_type = step.split("-")[1]
            with open(os.path.join("chains", chain_name, step), "r") as f:
                prompt = f.read()
            if step_number not in chain_data:
                chain_data[step_number] = {}
            chain_data[step_number][prompt_type] = prompt
        return chain_data

    def add_chain(self, chain_name):
        os.mkdir(os.path.join("chains", chain_name))

    def rename_chain(self, chain_name, new_name):
        os.rename(os.path.join("chains", chain_name), os.path.join("chains", new_name))

    def add_chain_step(self, chain_name, step_number, agent_name, prompt_type, prompt):
        with open(os.path.join("chains", chain_name, f"{step_number}-{agent_name}-{prompt_type}.txt"), "w") as f:
            f.write(prompt)

    def add_step(self, chain_name, step_number, prompt_type, prompt):
        with open(os.path.join("chains", chain_name, f"{step_number}-{prompt_type}.txt"), "w") as f:
            f.write(prompt)

    def update_step(self, chain_name, old_step_number, new_step_number, prompt_type):
        os.rename(os.path.join("chains", chain_name, f"{old_step_number}-{prompt_type}.txt"),
                  os.path.join("chains", chain_name, f"{new_step_number}-{prompt_type}.txt"))

    def delete_step(self, chain_name, step_number):
        files_to_delete = glob.glob(os.path.join("chains", chain_name, f"{step_number}-*.txt"))
        for file_path in files_to_delete:
            os.remove(file_path)

    def move_step(self, chain_name, step_number, new_step_number, prompt_type):
        os.rename(os.path.join("chains", chain_name, f"{step_number}-{prompt_type}.txt"),
                  os.path.join("chains", chain_name, f"{new_step_number}-{prompt_type}.txt"))

    def delete_chain(self, chain_name):
        shutil.rmtree(os.path.join("chains", chain_name))

    def delete_chain_step(self, chain_name, step_number):
        for file in glob.glob(os.path.join("chains", chain_name, f"{step_number}-*.txt")):
            os.remove(file)

    def get_step(self, chain_name, step_number):
        step_files = glob.glob(os.path.join("chains", chain_name, f"{step_number}-*.txt"))
        step_data = {}
        for file in step_files:
            prompt_type = file.split("-")[1].split(".")[0]
            with open(file, "r") as f:
                prompt = f.read()
            step_data[prompt_type] = prompt
        return step_data

    def get_steps(self, chain_name):
        chain_steps = os.listdir(os.path.join("chains", chain_name))
        steps = sorted(chain_steps, key=lambda x: int(x.split("-")[0]))
        step_data = {}
        for step in steps:
            step_number = int(step.split("-")[0])
            step_data[step_number] = self.get_step(chain_name, step_number)
        return step_data

    def load_memory(self):
        if os.path.isfile(self.memory_file):
            with open(self.memory_file, "r") as file:
                memory = yaml.safe_load(file)
                if memory is None:
                    memory = {"interactions": []}
        else:
            memory = {"interactions": []}
        return memory

    def save_memory(self):
        with open(self.memory_file, "w") as file:
            yaml.safe_dump(self.memory, file)

    def log_interaction(self, role: str, message: str):
        self.memory["interactions"].append({"role": role, "message": message})
        self.save_memory()
    
    def add_prompt(self, prompt_name, prompt):
        # if prompts folder does not exist, create it
        if not os.path.exists("prompts"):
            os.mkdir("prompts")
        # if prompt file does not exist, create it
        if not os.path.exists(os.path.join("prompts", f"{prompt_name}.txt")):
            with open(os.path.join("prompts", f"{prompt_name}.txt"), "w") as f:
                f.write(prompt)
        else:
            raise Exception("Prompt already exists")
        
    def get_prompt(self, prompt_name):
        with open(os.path.join("prompts", f"{prompt_name}.txt"), "r") as f:
            prompt = f.read()
        return prompt
    
    def get_prompts(self):
        # Create the path if it doesn't exist
        if not os.path.exists("prompts"):
            os.mkdir("prompts")
        prompts = os.listdir("prompts")
        return prompts
    
    def delete_prompt(self, prompt_name):
        os.remove(os.path.join("prompts", f"{prompt_name}.txt"))

    def update_prompt(self, prompt_name, prompt):
        with open(os.path.join("prompts", f"{prompt_name}.txt"), "w") as f:
            f.write(prompt)