"""Movable content regions and expressed relationships for 37 reference pages.

Coordinates are SVG logical pixels on a 1280 x 720 canvas, not PowerPoint
points.  Bounds follow the current original compositions in
``reference_pages_a.py`` and ``reference_pages_b.py``.  They describe examples,
not mandatory templates.  Normal page titles, subtitles, rules and footers are
not content regions.  A chapter statement or closing message can itself be the
page's content.  Cross-region connectors are intentionally outside the groups.

Relationship types:
  sequence: explicit information, argument or task progression; not by itself
    a claim of biological causation, elapsed time or completed work.
  supports: the stated contribution of evidence, an explanation or a resource
    to the target judgment; the label preserves the contribution's scope.
  converges: independent paths feed a shared stage or endpoint.
  feedback: named observations or errors return to an earlier decision stage.
  constrains: conditions or boundaries limit the target's interpretation.
  correspondence: matched conditions, scales or whole/local positions, with
    no implied temporal order or causal claim.

Relationships may be expressed by page text as well as by visible connectors.
No relationships are invented merely to join parallel panels.  The caller may
assign element IDs by geometry and add ``member_ids`` to the returned copy.
This module performs no file access and has no third-party dependencies.
"""

from copy import deepcopy


def _r(identifier, label, role, x, y, w, h):
    return dict(id=identifier, label=label, role=role, x=x, y=y, w=w, h=h)


def _e(source, target, kind, label):
    return {'from': source, 'to': target, 'type': kind, 'label': label}


def _page(regions, relationships=()):
    return dict(regions=regions, relationships=list(relationships))


def _conclusion(label):
    return _r('conclusion', label, 'conclusion', 50, 630, 1180, 50)


_PAGES = {
    1: _page([
        _r('scope', '研究范围：结构表征、性能比较与可检验设计依据', 'context', 65, 377, 655, 112),
        _r('object', '多孔材料整体与层状结构示意', 'scientific_object', 760, 6, 520, 680),
    ]),
    2: _page([
        _r('structure', '结构表征：形貌测量、参数提取、差异定位', 'navigation', 50, 145, 1180, 101),
        _r('mechanism', '传输机制：路径建模、约束分析、机制检验', 'navigation', 50, 262, 1180, 101),
        _r('performance', '性能评价：统一条件、平行测量、证据比较', 'navigation', 50, 379, 1180, 101),
        _r('iteration', '迭代设计：选择变量、新增实验、更新认识', 'navigation', 50, 496, 1180, 101),
    ]),
    3: _page([
        _r('chapter_statement', '章节命题与概括：建立结构和性能的可检验联系', 'chapter_statement', 65, 235, 705, 313),
        _r('structure_parameters', '结构参数：孔径、连通性与厚度', 'process', 832, 171, 341, 109),
        _r('mechanism_hypothesis', '机制假设：路径、阻力与边界条件', 'process', 832, 324, 341, 109),
        _r('independent_test', '独立检验：对照、重复与适用范围', 'validation', 832, 477, 341, 109),
        _r('status', '研究进展：验证方案制定中', 'status', 68, 599, 690, 38),
    ], [
        _e('structure_parameters', 'mechanism_hypothesis', 'sequence', '以结构参数建立可检验的机制假设'),
        _e('mechanism_hypothesis', 'independent_test', 'sequence', '将假设交给针对性对照与独立检验'),
    ]),
    4: _page([
        _r('sample_structure', '样本与结构：建立可追溯的研究对象', 'resource', 50, 161, 260, 399),
        _r('preparation_measurement', '制备与测量：形成可比较数据', 'resource', 330, 161, 260, 399),
        _r('features_model', '特征与模型：提出待检验假设', 'analysis', 690, 161, 260, 399),
        _r('independent_validation', '独立验证：对照、重复与反馈', 'validation', 970, 161, 260, 399),
        _conclusion('共同目标：把资源、计算与实验组织成连续过程'),
    ], [
        _e(source, 'conclusion', 'converges', '作为互补能力共同支撑材料评价；面板之间不强设先后')
        for source in ('sample_structure', 'preparation_measurement', 'features_model', 'independent_validation')
    ]),
    5: _page([
        _r('environment', '应用环境：温度与暴露时间限定工作边界', 'context', 50, 151, 570, 230),
        _r('object', '结构对象：孔道、界面和有效厚度', 'scientific_object', 660, 151, 570, 230),
        _r('metrics', '评价指标：传输响应与机械稳定性', 'criterion', 50, 388, 570, 238),
        _r('validation', '验证条件：独立批次与条件覆盖', 'validation', 660, 388, 570, 238),
    ]),
    6: _page([
        _r('structure_problem', '难点：结构差异难比较', 'problem', 50, 147, 281, 139),
        _r('structure_action', '对应动作：统一表征参数并提取可比特征', 'response', 422, 147, 808, 155),
        _r('signal_problem', '难点：响应来源不明确', 'problem', 50, 309, 281, 139),
        _r('signal_action', '对应动作：组合机制与定量证据并设置对照', 'response', 422, 309, 808, 155),
        _r('transfer_problem', '难点：结果跨条件波动', 'problem', 50, 471, 281, 139),
        _r('transfer_action', '对应动作：独立实验检查外推范围', 'response', 422, 471, 808, 157),
    ], [
        _e('structure_problem', 'structure_action', 'sequence', '以结构难点选择针对性的比较动作'),
        _e('signal_problem', 'signal_action', 'sequence', '以响应来源问题选择机制和定量对照'),
        _e('transfer_problem', 'transfer_action', 'sequence', '以跨条件波动选择独立外推检验'),
    ]),
    7: _page([
        _r('dimensions', '两路线共享输入、处理、读出和比较维度', 'comparison_guide', 50, 144, 1180, 35),
        _r('structure_input', '结构路线：输入对象与结构调节', 'process', 50, 198, 234, 192),
        _r('structure_strategy', '结构路线：控制变量与处理记录', 'process', 370, 228, 212, 139),
        _r('structure_readout', '结构路线：响应测量', 'evidence', 650, 228, 251, 179),
        _r('structure_comparison', '结构路线：统一基准、对照与代价比较', 'criterion', 986, 237, 244, 143),
        _r('interface_input', '界面路线：输入对象与界面调节', 'process', 50, 411, 234, 197),
        _r('interface_strategy', '界面路线：控制变量与处理记录', 'process', 370, 441, 212, 139),
        _r('interface_readout', '界面路线：响应测量', 'evidence', 650, 441, 251, 179),
        _r('interface_comparison', '界面路线：统一基准、对照与代价比较', 'criterion', 986, 450, 244, 143),
    ], [
        _e('structure_input', 'structure_strategy', 'sequence', '选择结构路线的可控变量'),
        _e('structure_strategy', 'structure_readout', 'sequence', '保持其余条件后测量响应'),
        _e('structure_readout', 'structure_comparison', 'sequence', '按统一基准比较响应与代价'),
        _e('interface_input', 'interface_strategy', 'sequence', '选择界面路线的可控变量'),
        _e('interface_strategy', 'interface_readout', 'sequence', '保持其余条件后测量响应'),
        _e('interface_readout', 'interface_comparison', 'sequence', '按统一基准比较响应与代价'),
        _e('structure_comparison', 'interface_comparison', 'correspondence', '两路线匹配同一评价维度；不是两条路线相互引起'),
    ]),
    8: _page([
        _r('observations', '已有观测：结构图、响应曲线与条件差异', 'evidence', 50, 145, 564, 410),
        _r('challenges', '当前挑战：混杂变化、独立对照与可检验变量', 'problem', 665, 145, 565, 410),
        _conclusion('研究切入点：以可控变量连接观测与机制检验'),
    ], [
        _e('observations', 'challenges', 'supports', '已有观测及其解释缺口定位当前研究问题'),
        _e('challenges', 'conclusion', 'constrains', '未解决问题限定后续可控变量与检验重点'),
    ]),
    9: _page([
        _r('levels', '行层级：挑战、关键问题、方法与验证目标', 'reading_guide', 50, 148, 122, 480),
        *[
            _r(f'{key}_{stage}', label, role, x, y, 326, h)
            for x, key, labels in (
                (202, 'structure', ('结构非均匀', '局部差异来自哪里', '统一结构描述', '识别可控因素')),
                (552, 'response', ('响应相互叠加', '哪一过程主导变化', '分离响应特征', '检验机制解释')),
                (902, 'scope', ('条件外推不明', '结论可适用到哪里', '扩展条件验证', '确定适用范围')))
            for (stage, role, y, h), label in zip(
                (('challenge', 'problem', 148, 67), ('question', 'question', 257, 67),
                 ('method', 'method', 367, 172), ('goal', 'validation_goal', 561, 67)), labels)
        ],
    ], [
        _e(f'{key}_{a}', f'{key}_{b}', 'sequence', label)
        for key in ('structure', 'response', 'scope')
        for a, b, label in (
            ('challenge', 'question', '将挑战细化为可回答的问题'),
            ('question', 'method', '按问题选择对应方法'),
            ('method', 'goal', '方法产出用于检验本列目标'))
    ]),
    10: _page([
        _r('acquisition', '结构采集：样本记录、图像与结构参数表', 'process', 50, 170, 261, 389),
        _r('features', '特征提取：归一化与条件特征矩阵', 'process', 359, 170, 261, 389),
        _r('selection', '候选筛选：效果、约束与优先验证集合', 'process', 668, 170, 261, 389),
        _r('experiment', '实验反馈：独立制备测量与偏差记录', 'validation', 977, 170, 261, 389),
        _r('constraints', '贯穿约束：样本追溯、统一基准与可复核处理', 'constraint', 50, 590, 1180, 53),
    ], [
        _e('acquisition', 'features', 'sequence', '结构采集产出进入特征整理'),
        _e('features', 'selection', 'sequence', '特征矩阵用于候选比较与筛选'),
        _e('selection', 'experiment', 'sequence', '优先集合进入独立实验检验'),
        *[_e('constraints', node, 'constrains', '统一追溯、评价基准和数据处理要求')
          for node in ('acquisition', 'features', 'selection', 'experiment')],
    ]),
    11: _page([
        _r('pattern', '并行线索：已知模式检索', 'discovery', 50, 146, 380, 163),
        _r('structure', '并行线索：空间结构比较', 'discovery', 50, 309, 380, 152),
        _r('neighbors', '并行线索：特征空间近邻', 'discovery', 50, 472, 380, 152),
        _r('screening', '候选汇总与筛选：质量、约束和验证对象', 'selection', 527, 196, 286, 356),
        _r('validation', '共同实验验证：统一条件、对照与偏差记录', 'validation', 908, 196, 322, 356),
        _conclusion('并行发现共享筛选与检验依据'),
    ], [
        *[_e(source, 'screening', 'converges', '该发现通道提供保留来源与条件的候选')
          for source in ('pattern', 'structure', 'neighbors')],
        _e('screening', 'validation', 'sequence', '筛选后的候选进入统一实验检验'),
    ]),
    12: _page([
        _r('constraints', '共同约束：结构可控、性能可比、结果可复现', 'constraint', 50, 149, 222, 464),
        _r('structure', '结构调节：组成形态与设计空间', 'method', 310, 149, 288, 464),
        _r('mechanism', '机制分析：边界解释与假设检验', 'method', 620, 149, 288, 464),
        _r('performance', '性能验证：统一评价与跨条件检验', 'validation', 930, 149, 288, 464),
    ], [
        _e('constraints', target, 'constrains', '三类共同约束贯穿该技术措施；不把右侧三栏强设成时间顺序')
        for target in ('structure', 'mechanism', 'performance')
    ]),
    13: _page([
        _r('whole', '整体结构及红框关键连接区域', 'scientific_object', 50, 145, 462, 399),
        _r('local', '对应红框位置的局部放大与机制假设', 'local_detail', 572, 145, 302, 414),
        _r('response', '机制与响应：可测读出和针对性对照', 'validation', 953, 145, 277, 414),
        _conclusion('以位置对应的局部特征提出可测假设'),
    ], [
        _e('whole', 'local', 'correspondence', '整体红框位置对应局部放大；不是任意近景拼接'),
        _e('local', 'response', 'sequence', '由局部机制假设选择响应与针对性对照'),
    ]),
    14: _page([
        _r('matrix', '响应矩阵：条件、参数分组、读图说明与颜色标尺', 'evidence', 50, 148, 785, 493),
        _r('design', '实验设计：处理条件、参数范围、基准和重复', 'experimental_design', 871, 148, 359, 496),
    ], [
        _e('design', 'matrix', 'constrains', '侧栏实验设计限定矩阵单元的含义及可比较范围'),
    ]),
    15: _page([
        _r('observations', '观测与特征：输入、学习目标和数据划分', 'model_input', 50, 147, 366, 418),
        _r('model', '模型与评估：预测误差、独立观测和适用范围', 'model_evaluation', 488, 147, 324, 418),
        _r('recommendation', '推荐与检验：约束排序、候选条件和实验更新', 'validation', 884, 147, 346, 418),
        _r('conclusion', '预测指导选择，实验决定结论', 'conclusion', 50, 592, 1180, 55),
    ], [
        _e('observations', 'model', 'sequence', '观测特征与响应进入训练和独立评估'),
        _e('model', 'recommendation', 'sequence', '模型评估后的排序指导实验候选选择'),
        _e('recommendation', 'model', 'feedback', '页内文字说明：实验结果用于更新模型'),
    ]),
    16: _page([
        _r('response', '响应特征：曲线形状、评价区间与测试条件', 'evidence', 50, 150, 565, 477),
        _r('agreement', '测量预测一致性：偏差分布与独立检验', 'evidence', 665, 150, 565, 477),
    ]),
    17: _page([
        _r('interface', '原理层：多层界面与局部传递路径', 'mechanism', 50, 134, 318, 224),
        _r('hypothesis', '变量、扩散驻留过程与可测预测', 'hypothesis', 445, 183, 327, 143),
        _r('prediction', '动力学预测：不同层间条件的时间响应', 'prediction', 850, 151, 355, 216),
        *[_r(identifier, label, 'validation_step', 50+i*243, 411, 208, 214)
          for i, (identifier, label) in enumerate((
              ('preparation', '制备梯度：只改变层间条件'), ('structure_check', '结构核验：确认层状结构'),
              ('measurement', '动态测量：完整时序与空白'), ('fitting', '联合拟合：参数与残差'),
              ('replication', '交叉验证：换批次核对预测方向')))],
        _conclusion('验证结构改变能否引起预期动力学变化'),
    ], [
        _e('interface', 'hypothesis', 'sequence', '从界面路径提出变量与中间过程'),
        _e('hypothesis', 'prediction', 'sequence', '机制假设给出可测的动态响应预测'),
        _e('prediction', 'measurement', 'constrains', '预测在实验前限定要记录的动力学变化'),
        *[_e(a, b, 'sequence', label) for a, b, label in (
            ('preparation', 'structure_check', '制备梯度进入结构质量核验'),
            ('structure_check', 'measurement', '合格结构样品进入动态测量'),
            ('measurement', 'fitting', '完整时序用于联合拟合与残差检查'),
            ('fitting', 'replication', '拟合后由独立批次核对方向'))],
        _e('replication', 'conclusion', 'supports', '独立批次检验预先提出的结构—动力学预测'),
    ]),
    18: _page([
        _r('morphology', '形貌证据：空间分布与结构完整性', 'evidence', 50, 145, 574, 227),
        _r('chemistry', '化学证据：初始、循环中与循环后特征信号', 'evidence', 655, 145, 575, 227),
        _r('repeatability', '重复性证据：独立批次偏差与异常回查', 'evidence', 50, 398, 574, 227),
        _r('function', '功能证据：循环衰减、漂移与空白', 'evidence', 655, 398, 575, 227),
        _conclusion('四类证据共同限定稳定性判断范围'),
    ], [_e(source, 'conclusion', 'supports', '共同支持稳定性判断的一个独立维度；四格之间没有时间链')
        for source in ('morphology', 'chemistry', 'repeatability', 'function')]),
    19: _page([
        _r('screening', '辅助证据：配方与处理梯度的筛选范围', 'screening', 50, 145, 345, 220),
        _r('structure', '候选结构示意及其解释范围', 'mechanism_hypothesis', 50, 389, 345, 236),
        _r('main_response', '主证据：响应曲线、候选窗口与两侧限制', 'evidence', 426, 145, 804, 480),
        _conclusion('先定位窗口，再解释两侧限制因素'),
    ], [
        _e('screening', 'main_response', 'constrains', '筛选范围限定主响应曲线所比较的条件'),
        _e('structure', 'main_response', 'supports', '结构示意辅助解释响应窗口；不作为独立测量结果'),
        _e('main_response', 'conclusion', 'supports', '主要响应曲线定位窗口及其边界'),
    ]),
    20: _page([
        _r('interface', '纳米级局部界面', 'scale_view', 50, 145, 300, 241),
        _r('porous', '微米级多孔结构', 'scale_view', 379, 145, 391, 241),
        _r('specimen', '毫米级整体样品', 'scale_view', 800, 145, 430, 241),
        _r('constraints', '跨尺度对照表：固定条件、观测对象与判断边界', 'constraint', 50, 396, 1180, 218),
        _conclusion('同一对象的不同尺度回答不同层级问题'),
    ], [
        _e('interface', 'porous', 'correspondence', '由局部界面转到多孔结构的尺度对应，非时间过程'),
        _e('porous', 'specimen', 'correspondence', '由多孔结构转到整体样品的尺度对应，非因果证明'),
        *[_e('constraints', target, 'constrains', '本列条件、读出和判断边界与对应尺度逐项匹配')
          for target in ('interface', 'porous', 'specimen')],
    ]),
    21: _page([
        _r('unify', '方法一：同批原料与初始状态记录', 'method', 50, 158, 238, 113),
        _r('isolate', '方法二：单变量处理梯度与并行参照', 'method', 50, 312, 238, 113),
        _r('replicate', '方法三：换批次复核与误差回查', 'method', 50, 466, 238, 121),
        _r('initial_state', '结果图：初始形貌分布', 'evidence', 335, 145, 432, 227),
        _r('conditions', '结果图：配方—条件响应矩阵', 'evidence', 798, 145, 432, 227),
        _r('dynamic', '结果图：参照与处理的动态响应', 'evidence', 335, 395, 432, 230),
        _r('agreement', '结果图：盲测批次预测一致性', 'evidence', 798, 395, 432, 230),
        _conclusion('输入与单变量对照确定差异来源，独立复核限定推广'),
    ], [
        _e('unify', 'isolate', 'sequence', '统一输入后实施单变量比较'),
        _e('isolate', 'replicate', 'sequence', '变量效应进入独立批次复核'),
        _e('unify', 'initial_state', 'correspondence', '初始状态图核对统一输入'),
        _e('isolate', 'conditions', 'correspondence', '条件矩阵对应配方和处理梯度'),
        _e('isolate', 'dynamic', 'correspondence', '动态响应对应单变量比较'),
        _e('replicate', 'agreement', 'correspondence', '一致性散点对应独立批次复核'),
    ]),
    22: _page([
        _r('optical_chain', '光学测量链路：光源、选波、样品、探测与空白参照通道', 'measurement_system', 50, 132, 680, 289),
        _r('microscopy', '补充能力：显微观察与异常定位', 'resource', 780, 132, 450, 182),
        _r('spectroscopy', '补充能力：谱学记录与副产物线索', 'resource', 780, 322, 450, 130),
        _r('calibration', '共同核验：波长强度基准、空白并行、同条件复测', 'criterion', 50, 478, 1180, 148),
        _conclusion('设备能力应对应具体可测判断'),
    ], [_e('calibration', target, 'constrains', '使用前按对应测量能力核对基准、参照和复测要求')
        for target in ('optical_chain', 'microscopy', 'spectroscopy')]),
    23: _page([
        _r('solution_route', '溶液组装路线：溶剂环境、界面形成与样品记录', 'parallel_route', 50, 148, 1180, 171),
        _r('deposition_route', '表面沉积路线：基底状态、负载控制与样品记录', 'parallel_route', 50, 347, 1180, 171),
        _r('shared_validation', '共享验证：统一归一化、盲法动态读出和独立复核', 'validation', 50, 559, 1180, 67),
        _conclusion('两路线在共同测量端点下比较'),
    ], [
        _e('solution_route', 'shared_validation', 'converges', '溶液组装样品进入共享验证端点'),
        _e('deposition_route', 'shared_validation', 'converges', '表面沉积样品进入同一验证端点'),
        _e('shared_validation', 'conclusion', 'supports', '共同条件使两路线的端点比较有明确口径'),
    ]),
    24: _page([
        _r('windows', '阶段窗口一至六：计划横轴而非实际工期承诺', 'schedule_scale', 352, 141, 792, 36),
        _r('baseline', '任务：基准与误差范围', 'planned_task', 50, 193, 1180, 53),
        _r('screening', '任务：小规模条件筛选', 'planned_task', 50, 255, 1180, 53),
        _r('replication', '任务：候选样品独立复测', 'planned_task', 50, 317, 1180, 53),
        _r('failure_modes', '任务：失效模式与耐受窗口', 'planned_task', 50, 379, 1180, 53),
        _r('delivery', '任务：汇总与可复现交付', 'planned_task', 50, 441, 1180, 53),
        _r('baseline_milestone', '里程碑：基准可用，误差边界明确', 'milestone', 230, 532, 285, 81),
        _r('candidate_milestone', '里程碑：候选收敛，进入独立复测', 'milestone', 554, 532, 285, 81),
        _r('delivery_milestone', '里程碑：数据与条件可追溯，结果可交付', 'milestone', 894, 532, 336, 81),
        _conclusion('阶段产物决定下一步进入及范围收缩'),
    ], [
        _e('baseline', 'screening', 'sequence', '基准完成后启动筛选；前一步验收产物是后一步的前提'),
        _e('screening', 'replication', 'sequence', '候选筛选收敛后进入独立复测'),
        _e('replication', 'failure_modes', 'sequence', '独立复测完成后进入失效模式与耐受窗口分析'),
        _e('failure_modes', 'delivery', 'sequence', '失效和耐受边界明确后汇总并交付可复现结果'),
        _e('baseline', 'baseline_milestone', 'supports', '以明确误差边界验收基准'),
        _e('screening', 'candidate_milestone', 'supports', '以候选收敛验收筛选阶段'),
        _e('delivery', 'delivery_milestone', 'supports', '以数据与条件可追溯验收交付'),
    ]),
    25: _page([
        _r('columns', '矩阵列：研究任务、实施方法与可测产出', 'matrix_guide', 50, 148, 1180, 35),
        _r('window_row', '定位窗口：条件覆盖与热图，输出连续响应区域', 'task_method_output', 50, 191, 1180, 140),
        _r('mechanism_row', '解释来源：谱学与动态测量，输出特征和速率参数', 'task_method_output', 50, 332, 1180, 140),
        _r('replication_row', '检验重复性：留出批次，输出跨批次误差分布', 'task_method_output', 50, 473, 1180, 140),
        _conclusion('每项方法对应可记录、可比较的产出'),
    ]),
    26: _page([
        _r('structures', '输入：结构与配方记录', 'input', 97, 146, 299, 55),
        _r('measurements', '输入：历史测量与对照', 'input', 490, 146, 299, 55),
        _r('boundaries', '输入：条件边界与成本', 'constraint_input', 883, 146, 299, 55),
        _r('computation', '计算工作区：统一口径、响应预测、不确定性与候选条件', 'computation', 75, 251, 500, 271),
        _r('experiment', '实验工作区：候选制备、参照信号、实测误差与异常记录', 'experiment', 705, 251, 500, 271),
        _r('returned_data', '数据回流：实测预测残差、失败条件与新增批次', 'feedback_data', 185, 558, 1020, 68),
        _conclusion('具体误差信息改变下一轮模型和实验选择'),
    ], [
        *[_e(source, target, 'converges', '共享输入总线为双域工作提供记录和边界')
          for source in ('structures', 'measurements', 'boundaries')
          for target in ('computation', 'experiment')],
        _e('computation', 'experiment', 'sequence', '计算向实验传递候选条件'),
        _e('experiment', 'computation', 'feedback', '实验向计算回传初步观测'),
        _e('experiment', 'returned_data', 'sequence', '汇总实测值、误差、失败条件和新批次'),
        _e('returned_data', 'computation', 'feedback', '用残差和失败条件更新可行范围及不确定性，再选下一轮测量'),
    ]),
    27: _page([
        _r('findings', '形成了什么：条件图谱、响应窗口与证据边界', 'summary', 50, 147, 520, 479),
        _r('credibility', '为何可信：独立批次、对照空白与追溯', 'validation_summary', 640, 153, 590, 237),
        _r('next_questions', '下一步：扩展环境条件并回查失效来源', 'future_question', 640, 418, 590, 208),
    ], [
        _e('credibility', 'findings', 'supports', '独立批次与可追溯对照为已有判断提供可信依据'),
        _e('findings', 'next_questions', 'constrains', '下一阶段验证由当前已测条件和证据边界限定'),
    ]),
    28: _page([
        _r('closing', '中心致谢语与研究讨论邀请', 'closing', 382, 243, 516, 191),
    ]),
    29: _page([
        _r('columns', '验收列：实施条件、判断依据、交付产物与进入资格', 'matrix_guide', 50, 148, 1180, 34),
        _r('samples', '样品与对照：来源批次记录、样品清单和可比较资格', 'acceptance_row', 50, 182, 1180, 108),
        _r('measurement', '测量与校准：基准漂移核验、原始时序和可测量资格', 'acceptance_row', 50, 290, 1180, 108),
        _r('analysis', '数据与分析：异常记录、可重放处理和可复现资格', 'acceptance_row', 50, 398, 1180, 108),
        _r('delivery', '结果与交付：独立复测、证据索引和可验收资格', 'acceptance_row', 50, 506, 1180, 108),
        _conclusion('实施条件以可检查记录和产物为依据'),
    ]),
    30: _page([
        *[_r(identifier, label, role, x, y, w, 145)
          for y, key, signal, action in (
              (151, 'weak_signal', '信号偏弱及接近空白的识别信号', '优化采集与背景核对，验收可区分响应'),
              (314, 'batch_variation', '批次离散及响应分布变宽', '锁定原料和步骤，验收可解释误差来源'),
              (477, 'condition_failure', '条件失效及高响应区不连续', '收缩可行区并逐项扩展，验收适用范围'))
          for identifier, label, role, x, w in (
              (key+'_signal', signal, 'risk_signal', 50, 492),
              (key+'_action', action, 'alternative_route', 623, 607))],
        _conclusion('风险、识别信号、替代动作和验证出口相连接'),
    ], [
        _e(key+'_signal', key+'_action', 'sequence', '本行识别信号触发对应替代路线，并以明确出口验收')
        for key in ('weak_signal', 'batch_variation', 'condition_failure')
    ]),
    31: _page([
        _r('map', '条件响应热图、外置标注与连续候选区', 'screening_evidence', 50, 132, 630, 338),
        _r('selection', '三步候选提取：排除边界、保留连通区、独立复测', 'selection_process', 50, 485, 622, 140),
        _r('distribution', '独立复核分布：响应提高、集中程度与尾部回查', 'validation', 744, 132, 486, 475),
        _conclusion('选择稳定区域并以整体分布复核'),
    ], [
        _e('map', 'selection', 'sequence', '从条件图谱按明确规则提取候选区域'),
        _e('selection', 'distribution', 'sequence', '候选集合进入独立复测并检查整体分布'),
        _e('distribution', 'conclusion', 'supports', '集合分布为候选稳定性提供依据，避免只看最高点'),
    ]),
    32: _page([
        _r('dynamic', '主要性能证据：动态响应幅度与建立速度', 'primary_evidence', 50, 147, 570, 350),
        _r('cycling', '主要性能证据：循环保持、漂移与衰减', 'primary_evidence', 660, 147, 570, 350),
        _r('extension', '拓展证据：外部介质变化下的谱形与响应方向', 'boundary_evidence', 50, 523, 1180, 107),
        _conclusion('响应能力、持续表现和迁移范围分别检验'),
    ], [
        _e('dynamic', 'conclusion', 'supports', '回答响应能力这一性能维度'),
        _e('cycling', 'conclusion', 'supports', '回答持续表现这一性能维度'),
        _e('extension', 'conclusion', 'constrains', '限定可迁移范围，不能替代两块主要性能证据'),
    ]),
    33: _page([
        _r('measurement_scene', '测量样本场景：条件记录、数据导出与处理版本', 'data_source', 50, 146, 321, 430),
        _r('analysis_workspace', '原创分析界面：结构定位、响应比较、条件矩阵和预测复核', 'platform_workspace', 453, 149, 776, 462),
        _conclusion('场景交代数据来源，界面编号解释具体动作'),
    ], [
        _e('measurement_scene', 'analysis_workspace', 'sequence', '实验场景导出的结构与响应数据进入分析工作区'),
    ]),
    34: _page([
        _r('measurement_record', '测量记录合成样张及红框证据区域', 'document_evidence', 68, 202, 265, 337),
        _r('measurement_claim', '测量判断：条件、单位、样本和读出可核对', 'supported_claim', 405, 252, 210, 225),
        _r('validation_record', '验证记录合成样张及红框证据区域', 'document_evidence', 684, 202, 265, 337),
        _r('validation_claim', '验证判断：对象处理和比较依据可追溯', 'supported_claim', 1021, 252, 209, 225),
        _conclusion('记录中的具体证据支持相邻判断'),
    ], [
        _e('measurement_record', 'measurement_claim', 'supports', '红框测量证据支持相邻可核对判断；记录为合成样张'),
        _e('validation_record', 'validation_claim', 'supports', '红框验证证据支持相邻追溯判断；记录为合成样张'),
    ]),
    35: _page([
        _r('acquisition', '采集：原始图像与样本条件', 'capability', 50, 151, 559, 141),
        _r('structure', '结构：可比较参数与差异定位', 'capability', 665, 151, 559, 141),
        _r('signal', '信号：测量整理、读出与基准', 'capability', 50, 313, 559, 141),
        _r('analysis', '分析：条件响应关联与模式比较', 'capability', 665, 313, 559, 141),
        _r('validation', '验证：独立实验、重复与偏差', 'capability', 50, 475, 559, 141),
        _r('output', '输出：图表、记录与后续复核', 'capability', 665, 475, 559, 146),
    ]),
    36: _page([
        _r('demand', '背景需求：复杂介质下持续响应及背景漂移', 'problem_context', 45, 145, 550, 210),
        _r('object', '对象选择：可独立调间距的复合膜与匹配对照', 'scientific_object', 685, 145, 545, 210),
        _r('subsystems', '子系统机制：界面富集与通道传递', 'mechanism_hypothesis', 685, 410, 545, 215),
        _r('testable_question', '可测问题：用搅拌和间距干预分离幅度与时间效应', 'testable_question', 50, 410, 545, 215),
        _conclusion('需求收束为可区分竞争解释的实验问题'),
    ], [
        _e('demand', 'object', 'sequence', '需求约束对象和可控变量的选择'),
        _e('object', 'subsystems', 'sequence', '从对象拆出分配与传递两个过程'),
        _e('subsystems', 'testable_question', 'sequence', '把过程转成可独立操作的条件与读出检验'),
        _e('testable_question', 'conclusion', 'supports', '终点给出能区分解释的具体实验问题；本页没有返回箭头'),
    ]),
    37: _page([
        _r('experimental_process', '实验栏：配方分组、同光路测量与时序对齐', 'experiment_process', 50, 145, 355, 226),
        _r('experimental_readout', '实验栏：完整时序、幅度与建立速度读出', 'experimental_evidence', 50, 371, 355, 254),
        _r('whole_specimen', '机制栏：等厚度整体样品与定位红框', 'scientific_object', 448, 145, 377, 219),
        _r('local_section', '机制栏：红框对应截面、上游富集与通道传递', 'local_mechanism', 448, 367, 377, 263),
        _r('model_features', '模型栏：层间距、厚度负载和动态参数输入', 'model_input', 868, 145, 362, 192),
        _r('model_prediction', '模型栏：预测与测量的一致性图', 'model_evaluation', 868, 365, 362, 170),
        _r('independent_validation', '模型栏：留出批次、盲测与残差回查策略', 'validation_plan', 889, 549, 317, 76),
        _conclusion('实验约束机制、位置支持特征构建，独立样本检验预测'),
    ], [
        _e('experimental_process', 'experimental_readout', 'sequence', '受控分组测量形成可比较的完整动态时序'),
        _e('experimental_readout', 'local_section', 'supports', '时序读出参数用于约束局部机制解释'),
        _e('whole_specimen', 'local_section', 'correspondence', '整体红框沿位置连线对应局部截面'),
        _e('model_features', 'model_prediction', 'sequence', '与实验同名的结构和动态变量进入模型预测'),
        _e('local_section', 'model_prediction', 'supports', '位置对应的局部机制支持特征构建和预测解释'),
        _e('model_prediction', 'independent_validation', 'sequence', '预测进入留出批次盲测与残差回查策略；不声称验证已完成'),
    ]),
}


def get_semantics(page_id):
    """Return a fresh ``regions``/``relationships`` dictionary for one page.

    ``page_id`` accepts an integer, its decimal string, or the public slug
    beginning with that page number.  Invalid IDs fail explicitly, so a missing
    semantic definition cannot silently become an empty page.
    """
    if isinstance(page_id, bool):
        raise ValueError('page_id must be a page number or numbered slug')
    if isinstance(page_id, int):
        number = page_id
    elif isinstance(page_id, str):
        prefix = page_id.split('-', 1)[0]
        if not prefix.isdecimal():
            raise ValueError('page_id must be a page number or numbered slug')
        number = int(prefix)
    else:
        raise ValueError('page_id must be a page number or numbered slug')
    if number not in _PAGES:
        raise KeyError('no reference semantics for page %s' % number)
    return deepcopy(_PAGES[number])
