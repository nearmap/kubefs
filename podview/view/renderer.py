from akube.model.object_model.status import ContainerStateTerminated
from podview.model.model import ContainerModel, PodModel, ScreenModel
from podview.view.buffer import ScreenBuffer, TextAlign


class BufferRenderer:
    def __init__(self, model: ScreenModel) -> None:
        self.model = model
        self.buffer = ScreenBuffer()

        self.cluster_name_width = 0
        self.pod_name_width = 0

        self.precompute_name_widths()

    def precompute_name_widths(self):
        clusters = self.model.iter_clusters()
        for cluster in clusters:
            cluster_name_len = len(cluster.context.short_name)
            if cluster_name_len > self.cluster_name_width:
                self.cluster_name_width = cluster_name_len

            for pod in cluster.iter_pods():
                pod_name_len = len(pod.name)
                if pod_name_len > self.pod_name_width:
                    self.pod_name_width = pod_name_len

    def render_container(self, container: ContainerModel, name_width: int) -> None:
        self.buffer.write(text=f"- {container.name}", width=name_width)

        with self.buffer.indent(width=4):
            val = container.state.current_value or ""
            self.buffer.write(text=val)

            with self.buffer.indent(width=1):
                val = container.state.current_elapsed_pretty
                if val:
                    self.buffer.write(text=val)

        with self.buffer.indent(width=4):
            # for containers in waiting/running show started/ready is False
            if container.state.current_value not in ('terminated',):
                if container.started.current_value not in (None, True):
                    code = f"- started: {container.started.current_value}"
                    self.buffer.write(text=code)
                    self.buffer.end_line()
                if container.ready.current_value not in (None, True):
                    code = f"- ready: {container.ready.current_value}"
                    self.buffer.write(text=code)
                    self.buffer.end_line()

            # show restartCount if not zero
            if container.restart_count.current_value > 0:
                val = f"- restartCount: {container.restart_count.current_value}"
                self.buffer.write(text=val)
                self.buffer.end_line()

            # show exitCode if not zero
            if container.exit_code.current_value not in (None, 0):
                code = f"- exitCode: {container.exit_code.current_value}"
                self.buffer.write(text=code)
                self.buffer.end_line()

            # show reason and message if set and not trivial
            if container.reason.current_value not in (None, "Completed"):
                code = f"- reason: {container.reason.current_value}"
                self.buffer.write(text=code)
                self.buffer.end_line()
            if container.message.current_value:
                code = f"- message: {container.message.current_value}"
                self.buffer.write(text=code)
                self.buffer.end_line()

    def render_pod(self, pod: PodModel) -> None:
        self.buffer.write(text=pod.name, width=self.pod_name_width)

        with self.buffer.indent(width=4):
            val = pod.phase.current_value and pod.phase.current_value.lower()
            self.buffer.write(text=val)

            with self.buffer.indent(width=1):
                val = pod.phase.current_elapsed_pretty
                if val:
                    self.buffer.write(text=val)

        containers = pod.iter_containers()
        cont_name_width = 0
        if containers:
            cont_name_width = max(len(f"- {cont.name}") for cont in containers)

        with self.buffer.indent(width=2):
            for container in containers:
                self.render_container(container, cont_name_width)

    def render(self) -> ScreenBuffer:
        self.buffer.write(text="podview", width=9)

        ela = self.model.elapsed.current_elapsed_pretty
        ela = f"[uptime: {ela}]"
        self.buffer.write(text=ela)
        self.buffer.end_line()
        self.buffer.end_line()

        clusters = self.model.iter_clusters()
        if not clusters:
            return self.buffer

        for cluster in clusters:
            self.buffer.write(
                text=cluster.context.short_name, width=self.cluster_name_width
            )

            with self.buffer.indent(width=3):
                for pod in cluster.iter_pods():
                    self.render_pod(pod)

        return self.buffer
