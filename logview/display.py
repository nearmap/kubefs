import json
import time
from typing import List

from kube.channels.generic import ChanReceiver
from kube.model.selector import ObjectSelector
from logview.target import PodTarget
from podview.model.colors import ColorPicker


class LogDisplay:
    def __init__(self) -> None:
        self.color_picker = ColorPicker.get_instance()

    def display_loop(self, targets: List[PodTarget], timeout_s: int):
        start_s = time.time()

        while time.time() - start_s < timeout_s:
            had_lines = False
            for target in targets:
                assert isinstance(target.oev_receiver, ChanReceiver)
                assert isinstance(target.selector, ObjectSelector)

                event = target.oev_receiver.recv_nowait()
                if event:
                    had_lines = True

                    assert isinstance(target.selector.podname, str)
                    podcolor = self.color_picker.get_for_image_hash(
                        target.selector.podname
                    )

                    podname = podcolor.stylize(target.selector.podname)
                    try:
                        dct = json.loads(event.object)
                        sev = dct.get("severity", "").upper()
                        msg = f"{dct!r}"

                        if sev:
                            sevcolor = self.color_picker.get_for_severity(sev)
                            if sevcolor:
                                sev = sevcolor.stylize(sev)
                                msg = sevcolor.stylize(msg)

                        block = f"{podname} {sev} {msg}"

                    except ValueError:
                        try:
                            line = event.object.decode()
                        except ValueError:
                            line = event.object

                        line = line.strip()
                        block = f"{podname} {line}"

                    print(block)

            if not had_lines:  # busy loop prevention
                time.sleep(0.05)
