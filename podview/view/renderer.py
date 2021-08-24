from podview.model.colors import ColorPicker
from podview.model.model import ContainerModel, PodModel, ScreenModel
from podview.view.buffer import ScreenBuffer, TextAlign


class BufferRenderer:
    def __init__(self, model: ScreenModel) -> None:
        self.model = model
        self.buffer = ScreenBuffer()

        self.cluster_name_width = 0
        self.pod_name_width = 0
        self.cont_name_width = 0
        self.status_width = 21  # terminated 12mo ago

        self.color_picker = ColorPicker.get_instance()

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
        warn_color = self.color_picker.get_warn_color()

        state = (
            container.state.current_value
            and container.state.current_value.lower()
            or ""
        )
        ela = container.state.current_elapsed_pretty
        color = container.state.current_color

        label = ""
        if state and ela:
            label = f"{state} {ela}"

        self.buffer.write(text=label, width=self.status_width, color=color)

        with self.buffer.indent(width=3):
            name_color = self.color_picker.get_for_container_name()
            self.buffer.write(text=f"{container.name}", color=name_color)

            wid = self.cont_name_width + 1 + (20)  # ' ' tag
            name_len = len(container.name)

            with self.buffer.indent(width=1):
                tag = container.image_tag.current_value
                color = self.color_picker.get_for_image_hash(tag)
                tag = tag and f"{tag[:20]}" or ""
                rem = wid - name_len
                self.buffer.write(text=tag, width=rem, color=color)

                # with self.buffer.indent(width=1):
                #     hash = container.image_hash.current_value or ''
                #     color = self.color_picker.get_for_image_hash(hash)
                #     hash = hash and f"@{hash[:6]}" or ''
                #     rem = wid - name_len - 12
                #     self.buffer.write(text=hash, width=rem, color=color)

                with self.buffer.indent(width=2):
                    if container.restart_count.current_value > 0:
                        val = f"[restarts: {container.restart_count.current_value}]"
                        self.buffer.write(text=val, color=name_color)

            with self.buffer.indent(width=2):
                # skipping 'started' and 'ready' because they are booleans and
                # not really insightful at all

                # show exitCode if not zero
                if container.exit_code.current_value not in (None, 0):
                    code = f"exitCode: {container.exit_code.current_value}"
                    self.buffer.write(text=code, color=warn_color)
                    self.buffer.end_line()

                # show reason and message if set and not trivial
                if container.reason.current_value not in (None, "Completed", "Error"):
                    code = f"reason: {container.reason.current_value}"
                    self.buffer.write(text=code, color=warn_color)
                    self.buffer.end_line()
                if container.message.current_value:
                    code = f"message: {container.message.current_value}"
                    self.buffer.write(text=code, color=warn_color)
                    self.buffer.end_line()

    def render_pod(self, pod: PodModel) -> None:
        warn_color = self.color_picker.get_warn_color()

        phase = pod.phase.current_value and pod.phase.current_value.lower() or ""
        ela = pod.phase.current_elapsed_pretty

        label = ""
        if phase and ela:
            label = f"{phase} {ela}"

        self.buffer.write(
            text=label, width=self.status_width, color=pod.phase.current_color
        )

        with self.buffer.indent(width=3):
            self.buffer.write(text=pod.name, width=self.pod_name_width)

        # TODO: bogus indent amount
        with self.buffer.indent(width=self.cluster_name_width + self.status_width + 8):
            # show reason and message if set and not trivial
            if pod.reason.current_value not in (None, "Completed", "Error"):
                code = f"reason: {pod.reason.current_value}"
                self.buffer.write(text=code, color=warn_color)
                self.buffer.end_line()
            if pod.message.current_value:
                code = f"message: {pod.message.current_value}"
                self.buffer.write(text=code, color=warn_color)
                self.buffer.end_line()

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
