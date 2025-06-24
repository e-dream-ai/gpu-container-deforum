from BackendWorker import BackendWorker
from threading import Event

class Predictor:
    def __init__(self):
        self.video_path = None

    def setup(self):
        pass  # If needed for init logic

    def predict(self, **kwargs):
        finished = Event()

        def handle_finished(result):
            self.video_path = result.get("video_path")
            finished.set()

        def handle_image(data):
            pass  # Optional hook

        worker = BackendWorker(params=kwargs, on_image_generated=handle_image, on_finished=handle_finished)
        worker.start()
        worker.join()
        finished.wait()

        return self.video_path
