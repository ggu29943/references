# 源 · 人物设定修订版 / Unreal 角色工程

按用户提供的[完整人物设定](docs/SOURCE_LORE.md)修订：成年约二十岁女性，170 cm，及腰白发，天蓝色无高光眼睛，素色柔软叠穿常服，展开约 6 m 的纯白双翼。制作解释与图文差异见 [建模依据](docs/CANON_MODEL_SPEC.md)。

这是可编辑、已绑定的角色制作版本。脸部与发型相似度、完整面部绑定、贴图烘焙和 Unreal 实机效果仍需继续精修与验证。

[普通形态](output/preview_front.png) · [面部](output/preview_portrait.png) · [展开羽翼](output/preview_winged.png) · [收拢羽翼](output/preview_folded.png) · [武器](output/preview_weapon.png) · [武器细节](output/preview_weapon_detail.png)

![源的展开羽翼](output/preview_winged.png)

## 模型与动作

| 文件 | 内容 |
| --- | --- |
| `output/Yuan_Character.blend` | 可编辑源场景、参考图片、90 根骨骼、基础闭眼形态、材质和动作 |
| `output/Yuan_Base.fbx` | 隐藏羽翼的常服角色，基础待机 |
| `output/Yuan_Winged.fbx` | 含展开羽翼的完整角色，基础待机 |
| `output/Yuan_Wings_Only.fbx` | 单独羽翼组件，共用角色骨架，便于 UE 运行时隐藏／显示 |
| `output/Yuan_Wings_Fold.fbx` | 骨骼收拢—展开动作；不是通过缩放羽翼实现 |
| `output/*LOD1.fbx`、`output/*LOD2.fbx` | 普通角色、完整羽翼角色、单独羽翼的自动减面级别 |
| `output/Yuan_Winged.glb` | 通用预览与交换文件 |

羽翼完全收拢后横向跨度约 0.85 m、前后占用约 1.4 m；翼骨长度保持不变。隐藏状态由网格可见性实现，不代表羽翼被切除或缩成很小的部件。已有 FK 骨骼与基础动作，尚无布料／毛发物理、完整控制器或生产级碰撞。

## 裁衡

新发的八张武器图包含银色镂空护手、花叶纹、深色剑鞘与珠饰剑穗，与早前文字中的素剑不同。当前主展示版按最新图片制作，文字版作为可选方案保留；最终采用哪一版仍待用户明确。这是两种外观方案，不是新增两把剑的故事设定。

- 图片版：`Caiheng_Sword`、`Caiheng_Sheath`、`Caiheng_Tassel`，各自提供 FBX 和 GLB。
- 文字版：`Caiheng_Text_Sword`、`Caiheng_Text_Sheath`，各自提供 FBX 和 GLB。
- 刃长“二尺五寸”暂按 1 尺 = 1/3 m 换算为约 0.8333 m；这一换算尚非世界观规定。
- 武器是独立静态部件，剑穗尚未绑定物理骨骼。Blender 的金属细纹和皮革微表面未烘焙为 UE 贴图；FBX／GLB 保留网格与基础材质。

[Unreal Engine 导入和组件设置](docs/UNREAL_IMPORT.md)

## 验证范围

检查记录位于 `output/validation.json`、`output/fbx_roundtrip_validation.json`、`output/prop_validation.json`、`output/lod_validation.json` 和 `output/wing_components.json`。包括尺寸、回导后骨骼与 UV、最多四个归一化权重、动画顶点位移、羽翼收拢跨度与骨长保持。预览均由实际网格渲染。

当前环境没有 Unreal Editor，没有生成 `.uasset` 或声称完成 UE 实机验收。自动 LOD、宽大羽翼、长发与衣袖仍需在目标项目里检查遮挡、穿插、物理和性能预算。表情仅含基础闭眼，没有口腔、口型或 ARKit 表情集。

## 重建与打包

Blender 4.3.2，无额外 Python 库：

```bash
blender -b --python-exit-code 1 --factory-startup -t 8 --python src/build.py
blender -b --python-exit-code 1 -t 4 --python src/export_lods.py
blender -b --python-exit-code 1 -t 4 --python src/export_wings.py
blender -b --python-exit-code 1 -t 4 --python src/validate_exports.py
blender -b --python-exit-code 1 -t 4 --python src/validate_props.py
python3 src/package_release.py
```

在第一条命令后追加 `-- --no-render` 可只生成模型。生成脚本会覆盖 `output/` 同名文件，手工继续雕刻时请另存源文件。人物和武器图片位于 `assets/reference/`；源场景打包了参考图。
