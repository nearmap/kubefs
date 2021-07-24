from podview.model.model import ScreenModel
from podview.view.buffer import ScreenBuffer


class BufferRenderer:
    def render(self, model: ScreenModel) -> ScreenBuffer:
        buffer = ScreenBuffer()

        clusters = model.iter_clusters()
        if not clusters:
            return buffer

        cluster_name_width = max(
            (len(cluster.context.short_name) for cluster in clusters)
        )

        for cluster in clusters:
            buffer.write(text=cluster.context.short_name, width=cluster_name_width)

            with buffer.indent(width=3):
                for pod in cluster.iter_pods():
                    buffer.write(text=pod.name)
                    buffer.end_line()

                    with buffer.indent(width=2):
                        for container in pod.iter_containers():
                            buffer.write(text=container.name)
                            buffer.end_line()

        return buffer

        # lines = []
        # lines.append(
        #     "%s    %s  %s (%s)    %s "
        #     % (
        #         cluster_model.context.short_name,
        #         pod_model.name,
        #         pod_model.phase.current_value,
        #         pod_model.phase.current_elapsed_pretty or "",
        #         pod_model.image_hash.current_value
        #         and pod_model.image_hash.current_value[:6]
        #         or "",
        #     )
        # )
        # for cont in pod_model.iter_containers():
        #     lines.append(
        #         "    %s  %s  %s"
        #         % (
        #             cont.name,
        #             cont.state.current_value,
        #             cont.image_hash.current_value and cont.image_hash.current_value[:6],
        #         )
        #     )
        # print("\n" + "\n".join(lines) + "\n")
