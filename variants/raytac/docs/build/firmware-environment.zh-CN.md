中文 | [English](firmware-environment.md)

# 从新检出的仓库构建 Raytac 固件

正常装配可直接使用[当前配套的 HEX 下载](../../hardware/usb-short-route/firmware/README.zh-CN.md)。本文用于重新构建。命令均从 YETI60 仓库根目录执行；当前 USB 短线候选板不能改刷保留参考板的固件。

## 主机所需软件

- 主机上的 Python 3.9 或更新版本及 Git。
- 正在运行的 Linux 容器 Docker 引擎，仓库和工作区目录需共享到其虚拟机中。Docker Desktop、Colima 均需能访问这些主机路径。主机临时目录可能没有共享；在本次测试的 Colima 配置下，默认的用户目录工作区能避开该问题。
- **容器内部**能访问镜像仓库及清单中的 Git 地址。主机浏览器能联网不代表容器能联网。镜像、依赖和构建目录还需要额外可用磁盘空间。
- 候选板封装脚本的原生测试需要主机 C 编译器，并支持 AddressSanitizer／UndefinedBehaviorSanitizer。已记录的 macOS 检查使用 Clang。编译及这些测试不需要实物键盘或调试器。

主机无需单独安装 west、Zephyr SDK 或 Python `devicetree` 包。构建镜像提供 west／ARM 工具链；主机脚本从锁定的 Zephyr 检出目录加载设备树解析器。[冻结清单](../../firmware/target/config/west.yml)固定了 56 个启用依赖，含项目 ZMK 分支与 Zephyr。容器固定为 `zmkfirmware/zmk-build-arm@sha256:edb1c953438c6f720ddb79c3762f3972013b7fbbaf4fff3592fc869983e7afc5`。

## 初始化与核对

```sh
python3 variants/raytac/scripts/prepare_yeti60_workspace.py
python3 variants/raytac/scripts/prepare_yeti60_workspace.py --check
```

第一条命令将原样清单复制到 `~/.cache/yeti60-zmk-workspace/config/west.yml`，执行本地 west 初始化、下载锁定依赖、执行 `west zephyr-export`，最后核对提交号和工作树。仅在缺少镜像时下载固定镜像。重复执行可继续中断的下载，不会重置或清理依赖仓库。若目录已有无关内容、清单变化、依赖提交变化、已跟踪文件修改或未跟踪源码，准备过程会停止并保留原内容。若有意维护修改过的依赖，请另选工作区。

`--check` 只核对现有工作区及镜像，不下载、不更新、不导出，但仍需 Docker 守护进程。两条命令均拒绝本地 west 项目／分组筛选覆盖，并在容器中禁用全局／系统级筛选覆盖。Git 所有权例外仅限于各个临时容器内的清单目录，不改主机 Git 配置。编译默认使用两个并行任务，以降低虚拟机共享文件系统的文件描述符压力。

若改用其他工作区，准备、构建和测试必须选择**同一个路径**：

```sh
export YETI60_ZMK_WORKSPACE="$HOME/.cache/yeti60-raytac-workspace"
python3 variants/raytac/scripts/prepare_yeti60_workspace.py
python3 variants/raytac/scripts/prepare_yeti60_workspace.py --check
```

构建脚本也支持 `--workspace <路径>`；环境变量同时适用于独立运行的目标／主机检查。使用自定义路径时，请在整个会话中保留该变量。支持包含空格的路径；不支持 Docker 绑定目录包含冒号。

## 复用已核对的依赖缓存

若另一个工作区已有完全相同的锁定依赖，west 可以从中克隆，避免重新下载项目历史：

```sh
python3 variants/raytac/scripts/prepare_yeti60_workspace.py \
  --workspace "$HOME/.cache/yeti60-raytac-workspace" \
  --cache-workspace "$HOME/.cache/yeti60-zmk-workspace"
export YETI60_ZMK_WORKSPACE="$HOME/.cache/yeti60-raytac-workspace"
python3 variants/raytac/scripts/prepare_yeti60_workspace.py --check
```

首次使用缓存初始化时请选一个新的目标目录。来源缓存按同一清单核对，并以只读方式挂载；目标目录包含独立检出。离线使用要求镜像已存在；缓存不能替代准确版本或构建来源记录。使用 Git alternates 的开发缓存还要求原始对象库持续可用；普通网络克隆无此依赖。

## 构建当前板

候选板封装脚本会先核对已发布的原生设计／CAD 证据。使用当前提交的配套文件：

```sh
python3 variants/raytac/scripts/build_usb_short_firmware.py
python3 variants/raytac/scripts/check_usb_short_firmware.py
```

脚本构建**正常版、校准版两套** ARM 固件，核对链接后的 USB／HID 结构和校准契约，并执行原生扫描、GPIO、按键链路及 NVS 测试。当前候选板 HEX／BIN 及证据发布到 `variants/raytac/hardware/usb-short-route/firmware/`。ELF 及中间文件保留在 `variants/raytac/.assembly-work/usb-short-build/`，以哈希记录。候选板构建不覆盖独立的参考固件。

`--host-tests-only` 要求本机已有成功构建，且固件输入保持一致，不能替代首次构建。板子或固件契约变化必须完整构建。单独的 `build_yeti60_firmware.py` 在 `firmware/releases/` 生成保留参考板的固件，仅用于参考工程工作。

## 故障处理

| 提示／现象 | 处理 |
|---|---|
| Docker 守护进程／镜像不可用 | 启动 Docker；不加 `--check` 执行准备以下载固定镜像。 |
| Docker 无法读取主机清单 | 将工作区共享给 Docker／Colima；重试同一命令，或使用默认用户目录路径。 |
| 拉取停滞／失败 | 检查容器内 DNS、HTTPS／代理及镜像仓库连接。恢复网络后重试准备；已有下载会保留。 |
| 清单／提交／工作树不符 | 保留现有工作，使用提交中的清单另建工作区。不要为了通过检查而删除本地修改。 |
| 缺少锁定的 Zephyr 或清单 | 先执行准备，不要安装任意版本的主机 `devicetree` 包。 |
| 原生／CAD 或固件证据过期 | 有意改动后重跑相应设计检查／完整构建；不能手改记录哈希来隐藏不一致。 |
| 目标编译失败 | 检查 Raytac 目录下 `.assembly-work/usb-short-build/.firmware-work/normal.log` 或 `calibrator.log`。 |

west 初始化／更新流程依据 [Zephyr 内置命令文档](https://docs.zephyrproject.org/latest/develop/west/built-in.html)。构建及主机测试通过不代表实物 USB 枚举、BLE 射频、静电容裕量、充电安全或装配验收。制造后继续执行[无外壳台架验收](../../OPEN-BENCH.zh-CN.md)。

## 本轮验证及边界

[新源码构建证据](../audit/published-source-build.json)记录：不复制本机项目构建目录的源码副本，使用从只读锁定缓存建立的独立 56 依赖工作区，成功构建正常版和校准版并执行目标／主机测试。重建后的 HEX／BIN 字节及校准标识不变。本轮另有 10 项环境回归检查。

当前 Colima 虚拟机的 GitHub HTTPS 超时／TLS 错误使纯网络首次下载未能完成，因此不将该路径计为通过。独立依赖工作区的创建和构建已验证，不能替代网络链路验证。

原生 KiCad 三维模型仍有单独的待修项：旧 KiCad 6／私有模型引用、U2／U4 的重复模型及本机库缺少 J2 的 SMT 插座模型。它们不属于本次固件构建通过范围；独立装配渲染与原生 KiCad 三维视图的来源不同，不能互相代替验收。
