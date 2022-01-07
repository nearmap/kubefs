import json
import time
from typing import Dict

from kube.channels.objects import OEvReceiver
from kube.model.selector import ObjectSelector
from podview.model.colors import ColorPicker


class LogDisplay:
    def __init__(self) -> None:
        self.color_picker = ColorPicker.get_instance()

    def display_loop(self, oev_receivers: Dict[ObjectSelector, OEvReceiver], timeout_s: int):
        start_s = time.time()

        while time.time() - start_s < timeout_s:
            had_lines = False
            for selector, oev_receiver in oev_receivers.items():
                event = oev_receiver.recv_nowait()
                if event:
                    had_lines = True
                    podcolor = self.color_picker.get_for_image_hash(selector.podname)

                    podname = podcolor.stylize(selector.podname)
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
                        block = f"{podname} {event.object}"

                    print(block)

            if not had_lines:  # busy loop prevention
                time.sleep(0.05)
