from podview.model.colors import Color, ColorPicker
from podview.model.model import ContainerModel, PodModel, ScreenModel
from podview.view.buffer import ScreenBuffer, TextAlign


class BufferRenderer:
    def __init__(self, model: ScreenModel) -> None:
        self.model = model
        self.buffer = ScreenBuffer()

        self.cluster_name_width = 0
        self.pod_name_width = 0
        self.cont_name_width = 0

        self.color_picker = ColorPicker.get_instance(contexts=[])

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

                for cont in pod.iter_containers():
                    cont_name_len = len(cont.name)
                    if cont_name_len > self.cont_name_width:
                        self.cont_name_width = cont_name_len

    def render_container(self, container: ContainerModel, name_width: int) -> None:
        self.buffer.write(text=f"{container.name}")

        wid = self.cont_name_width + 9  # : + hash
        name_len = len(container.name)

        with self.buffer.indent(width=0):
            hash = container.image_hash.current_value
            color = self.color_picker.get_for_image_hash(hash)
            if hash:
                rem = wid - name_len
                self.buffer.write(text=f":{hash[:8]}", width=rem, color=color)

            with self.buffer.indent(width=2):
                val = container.state.current_value or ""
                self.buffer.write(text=val, color=container.state.current_color)

                with self.buffer.indent(width=1):
                    val = container.state.current_elapsed_pretty
                    if val:
                        self.buffer.write(text=val, width=4)

        with self.buffer.indent(width=4):
            # for containers in waiting/running show started/ready is False
            if container.state.current_value not in ("terminated",):
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
            self.buffer.write(text=val, color=pod.phase.current_color)

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
        self.buffer.write(text="podview")

        with self.buffer.indent(width=2):
            cluster = self.model.cluster.current_value or "*"
            namespace = self.model.namespace.current_value or "*"
            pod = self.model.pod.current_value or "*"
            fmt = f"cluster:{cluster}  namespace:{namespace}  pod:{pod}"
            self.buffer.write(text=fmt, width=60, align=TextAlign.CENTER)

            with self.buffer.indent(width=2):
                ela = self.model.uptime.current_elapsed_pretty
                ela = f"uptime: {ela}"
                self.buffer.write(text=ela, width=12, align=TextAlign.RIGHT)
                self.buffer.end_line()
                self.buffer.end_line()

        clusters = self.model.iter_clusters()
        if not clusters:
            return self.buffer

        for cluster in clusters:
            self.buffer.write(
                text=cluster.name.current_value,
                width=self.cluster_name_width,
                color=cluster.name.current_color,
            )

            with self.buffer.indent(width=3):
                for pod in cluster.iter_pods():
                    self.render_pod(pod)

        return self.buffer
