# Unreal Engine 5 导入

本工程在 Blender 中生成并做了 FBX 回导测试，尚未在 Unreal Editor 实机验证。不同 UE5 版本和 FBX／Interchange 导入器的选项位置可能不同。

## 身体、羽翼与动作

1. 导入 `Yuan_Base.fbx`，启用 Skeletal Mesh、Import Morph Targets 和 Import Animations。首次 Skeleton 留空创建新骨架。
2. Import Uniform Scale 设为 1.0，启用场景单位转换（若提供）。源单位为米，UE 为厘米；角色中立网格高度应约 **170 cm**。
3. 可直接导入 `Yuan_Winged.fbx` 查看完整形态。若要运行时隐藏羽翼，应使用 **身体 + 独立羽翼组件**：导入 `Yuan_Wings_Only.fbx`，选择身体的同一 Skeleton。
4. 在角色蓝图中增加一个 SkeletalMeshComponent 放置独立羽翼，保持相同原点、旋转和单位缩放；可用 Set Leader Pose Component 跟随身体组件，或在 Animation Blueprint 使用 Copy Pose From Mesh。两者不要同时叠加。通过该羽翼组件的 Set Visibility 显隐，身体保留显示。
5. 将 `Yuan_Wings_Fold.fbx` 的动画导入同一 Skeleton。源动作 `Yuan_Wings_Fold_Open_4s` 在帧 1 展开、31–61 收拢、91–121 再展开；30 fps，约 4 秒。动画资产名称可能由导入器改写。先在骨架编辑器检查肩、肘、腕三段动作，再连接动画状态机。该动作是收放验证，没有宣称完成飞行动作库。
6. 基础待机源动作名为 `Yuan_Idle_4s`。`Blink_L` 与 `Blink_R` 位于多个眼部网格，驱动同名对应目标可共同闭合眼睛；导入器可能给形态键添加网格前缀。

展开翼展应约 **600 cm**。收拢采用真实骨骼转动而非缩放，当前收拢横向跨度约 85 cm、前后占用约 140 cm，骨长误差接近浮点精度；实际动作中仍应检查羽毛互相遮挡和衣物穿插。

## 材质

- 眼睛无高光是明确设定：眼白、虹膜和瞳孔在 UE 材质中将 **Specular = 0、Metallic = 0、Roughness = 1**，不加眼角膜高光层和发光点。
- 角色皮肤的轻微透光来自 Blender 次表面散射，UE 中需另设皮肤材质，不能直接照搬节点网络。
- 常服不含花形饰品和繁复刺绣。羽翼基础颜色为中性白，灯光阴影不代表羽毛本身变色。
- 参考基础颜色、金属度和粗糙度可查看 `output/materials.json`。纹理图集、法线烘焙和完整 UE 材质实例未制作。

## 武器

`Caiheng_Sword.fbx`、`Caiheng_Sheath.fbx`、`Caiheng_Tassel.fbx` 是图片版独立 Static Mesh。剑的原点在柄刃衔接处，剑刃沿局部 +Z；剑鞘原点在鞘口；剑穗原点在系绳悬挂点。可建立手掌 Socket 后调整附件 Transform。剑穗当前为静态网格，未设置布料、链条骨骼或刚体运动。

`Caiheng_Text_Sword.fbx`、`Caiheng_Text_Sheath.fbx` 是无护手、无纹饰、素白剑鞘的文字版。图文外观差异尚待用户最终选择。两版刃长约 83.33 cm，来自暂定的尺制换算，不是新确认的设定数值。

图片版金属花叶、镂空护手和剑穗是几何结构；皮革细纹和刃面微纹理是 Blender 材质节点效果，未烘焙，需在 UE 内补相应材质。文字版剑材质使用高粗糙度和零镜面以符合“不反光”。

## 重定向、LOD 与生产工作

90 根骨骼采用自定义人形结构，名称借鉴 UE 命名，但不是 Manny／Quinn 的相同骨架。使用 IK Rig 与 IK Retargeter，设置 pelvis 为 Retarget Root，映射四肢与脊柱，调整放松 A 姿的 Retarget Pose。没有附现成 Control Rig、IK Rig 或 PhysicsAsset。

头发、衣摆、袖子、腰带与羽翼骨骼可用于次级运动，但物理、碰撞和约束尚未配置。自动生成的 LOD1／LOD2 为独立 FBX，在 UE 中对应导入 LOD 并调整屏幕距离，特别检查细发丝、羽片边缘和形态键。面数以最新 JSON 验证记录为准。完整角色仍为高细节制作网格，材质槽合并、贴图烘焙、大动作变形修正和目标平台性能测试仍需继续完成。
