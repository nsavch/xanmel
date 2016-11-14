from xanmel.action import BaseAction


class PrintStdout(BaseAction):
    def run(self):
        print(self.properties['message'])


class ExecuteShellCommand(BaseAction):
    async def run(self):
        print(self.properties['cmd'])
