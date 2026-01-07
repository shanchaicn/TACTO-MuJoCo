"""MuJoCo + TACTO DIGIT demo (stable version).

Why this structure:
- MuJoCo viewer (GLFW/GLX) is interactive and should run in the main process/thread.
- TACTO uses pyrender/PyOpenGL offscreen rendering which can conflict with MuJoCo's
  OpenGL context when run in the same process.

So we run:
- Main process: MuJoCo simulation + viewer (you can move objects here)
- Child process: TACTO tactile rendering (offscreen), synchronized via qpos/qvel
"""

import logging
import multiprocessing as mp
import os
from pathlib import Path

import dm_control.mujoco
import hydra
import mujoco
import mujoco.viewer

log = logging.getLogger(__name__)


def _tacto_process(model_path: str, bg_path: str, object_urdf_path: str, tacto_kwargs: dict, conn):
    # Must be set BEFORE importing tacto/pyrender/OpenGL
    os.environ.setdefault("PYOPENGL_PLATFORM", "osmesa")

    import cv2
    import dm_control.mujoco
    import mujoco
    import tacto.sensor_mujoco as sensor

    physics = dm_control.mujoco.Physics.from_xml_path(model_path)
    digit_body = physics.model
    digit_body_data = physics.data

    bg = cv2.imread(bg_path) if bg_path else None
    digits = sensor.Sensor(digit_body, digit_body_data, **tacto_kwargs, background=bg)
    digits.add_camera(1, [0])

    # add object to tacto simulator
    digits.add_body(object_urdf_path, digit_body_data.body("base_link").id, 0)

    while True:
        # Drain the pipe and keep only the latest state to avoid lag.
        latest = None
        while conn.poll():
            latest = conn.recv()
        if latest is not None:
            qpos, qvel = latest
            digit_body_data._data.qpos[:] = qpos
            digit_body_data._data.qvel[:] = qvel
            mujoco.mj_forward(digit_body._model, digit_body_data._data)

        color, depth = digits.render(visualize_digit=False)
        digits.updateGUI(color, depth)


@hydra.main(version_base=None, config_path="conf", config_name="digit")
def main(cfg):
    repo_root = Path(__file__).resolve().parent
    bg_path = str((repo_root / "conf" / "bg_digit_240_320.jpg").resolve())
    model_path = str((repo_root / cfg.experiment.urdf_path).resolve())
    object_urdf_path = str((repo_root / cfg.object.urdf_path).resolve())

    log.info("Initializing world")

    # Main process MuJoCo
    physics = dm_control.mujoco.Physics.from_xml_path(model_path)
    digit_body = physics.model
    digit_body_data = physics.data

    # Start TACTO process
    tacto_proc = None
    tacto_conn = None
    if os.environ.get("TACTO_LAUNCH_TACTO", "1") == "1":
        ctx = mp.get_context("spawn")
        recv_conn, send_conn = ctx.Pipe(duplex=False)
        tacto_proc = ctx.Process(
            target=_tacto_process,
            args=(model_path, bg_path, object_urdf_path, dict(cfg.tacto), recv_conn),
            daemon=True,
        )
        tacto_proc.start()
        tacto_conn = send_conn

    try:
        with mujoco.viewer.launch_passive(digit_body._model, digit_body_data._data) as viewer:
            while viewer.is_running():
                mujoco.mj_step(digit_body._model, digit_body_data._data)

                if tacto_conn is not None:
                    try:
                        tacto_conn.send((digit_body_data._data.qpos.copy(), digit_body_data._data.qvel.copy()))
                    except (BrokenPipeError, EOFError):
                        tacto_conn = None

                viewer.sync()
    finally:
        if tacto_proc is not None:
            tacto_proc.terminate()
            tacto_proc.join(timeout=1.0)


if __name__ == "__main__":
    main()
