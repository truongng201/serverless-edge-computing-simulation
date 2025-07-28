class ContainerState:
    pass

class Config:
    DEFAULT_CONTAINER_IMAGE = "serverless-handler:latest"
    DEFAULT_CONTAINER_COMMAND = "sleep infinity"
    DEFAULT_CONTAINER_DETACH_MODE = True
    DEFAULT_CONTAINER_MEMORY_LIMIT = "256m"  # 256 MB