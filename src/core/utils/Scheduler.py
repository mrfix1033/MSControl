import time

class Scheduler:
    def __init__(self):
        self.tasks = []

    def schedule(self, func, delay1, delay_next=-1):
        # delays in ms
        self.tasks.append((func, time.time() + delay1, delay_next))

    def tick(self):
        current_time = time.time()
        remaining_tasks = []

        for task in self.tasks:
            if current_time >= task[1]:
                try:
                    task[0]()
                    if task[2] > 0:
                        task[1] = time.time()+task[2]
                        remaining_tasks.append(task)
                except Exception as e:
                    print(e)
            else:
                remaining_tasks.append(task)

        self.tasks = remaining_tasks