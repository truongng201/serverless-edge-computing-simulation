import docker
import time
from docker.models.containers import Container
from config import Config

class ServerlessContainer:
    def __init__(self, app_id):
        self.client = docker.from_env()
        self.image = Config.DEFAULT_CONTAINER_IMAGE
        self.command = Config.DEFAULT_CONTAINER_COMMAND
        self.detach_mode = Config.DEFAULT_CONTAINER_DETACH_MODE
        self.memory_limit = Config.DEFAULT_CONTAINER_MEMORY_LIMIT
        self.state = "COLD"
        self.container = None
        self.container_id = None
        self.app_id = app_id
        

    def _create(self):
        print(f"Starting container with image {self.image}...")
        self.container = self.client.containers.run(
            image=self.image,
            command=self.command,
            detach=self.detach_mode,
            mem_limit=self.memory_limit,
            name=f"fn-{self.app_id}-{int(time.time())}"  # Unique name based on app ID and timestamp
        )
        print(f"Container started with ID: {self.container.id}")
        self.container_id = self.container.id
        
        
    def build(self):
        print(f"Building container with image {self.image}...")
        try:
            self.client.images.build(path="functions/", tag=self.image)
            print(f"Image {self.image} built successfully.")
        except docker.errors.BuildError as e:
            print(f"Error building image: {e}")
            raise e
    
        
        
    def run_function(self):
        # Check if existing container is running
        if self.container and self.container.status == 'running':
            print(f"Container {self.container.id} is already running.")
            return
        else:
            self._create()
        
        print(f"Running function in container {self.container.id}...")
        self.container.start()
        self.state = "WARM"
        print("Function is running.")
        

    def stop(self):
        if self.container:
            print(f"Stopping container {self.container.id}...")
            self.container.stop()
            print("Container stopped.")
        else:
            print("No container to stop.")
    