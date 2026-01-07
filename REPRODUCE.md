### 这版“能跑”的改动点（你问的 1）

- **修复 MuJoCo viewer 不显示/崩溃**：把 MuJoCo viewer 从“子线程启动”改成“主线程 `launch_passive()` + 主循环里 `mj_step()`”，避免 `gladLoadGL error` 和段错误。
- **避免 TACTO(pyrender/PyOpenGL) 与 MuJoCo viewer 的 OpenGL 冲突**：把 TACTO 放到**子进程**跑，并通过 Pipe 同步主进程的 `qpos/qvel`，让触觉窗口跟 MuJoCo 同步，同时 MuJoCo 窗口仍可交互移动物体。
- **渲染后端策略**：`tacto/renderer.py` 不再无条件强制某个 `PYOPENGL_PLATFORM`（你也可以用环境变量覆盖）。
- **依赖版本对齐**：在 `requirements.txt`/环境里固定使用 `mujoco==2.3.7`、`dm-control==1.0.14`、`PyOpenGL==3.1.4`、`PyOpenGL-accelerate==3.1.4`（这是我们当时跑通的组合）。

涉及文件：
- `demo_mujoco_digit.py`
- `tacto/renderer.py`
- `requirements.txt`


### 如何保存并在另一台电脑复现（你问的 2）

#### 方式 A：推荐（Conda 一键复现）

把仓库拷到另一台机器后，在仓库根目录执行：

```bash
conda env create -f environment.yml
conda activate tactomjc_38
python demo_mujoco_digit.py
```

#### 方式 B：pip（无 conda）

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python demo_mujoco_digit.py
```

#### 系统依赖提醒

- 需要能开窗口：X11/Wayland + OpenGL 驱动正常（你这台是 NVIDIA，已 OK）
- 如果用 `PYOPENGL_PLATFORM=osmesa`，系统上要有 `libOSMesa`（你这台已经有 `libOSMesa.so`）


