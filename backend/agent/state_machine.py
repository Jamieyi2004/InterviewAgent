"""
面试流程状态机 —— 控制 Agent 在不同阶段的行为和阶段跳转

借鉴闲鱼客服Agent的设计思路：
1. 每个阶段有详细的行为指令
2. 阶段指令包含策略性指导，而非简单的描述
3. 支持根据上下文动态调整指令
"""

from enum import Enum
from typing import Optional, Dict

from config import DEFAULT_MAX_QUESTIONS


class InterviewStage(str, Enum):
    """面试阶段枚举"""
    OPENING = "opening"              # 开场寒暄
    CODING = "coding"                # 算法编程题
    BASIC_QA = "basic_qa"            # 基础知识 / 八股文
    PROJECT_DEEP = "project_deep"    # 项目经历深挖
    SUMMARY = "summary"              # 总结阶段
    FINISHED = "finished"            # 面试结束

    @classmethod
    def ordered(cls) -> list["InterviewStage"]:
        """返回有序的阶段列表（不含 FINISHED）"""
        return [cls.OPENING, cls.CODING, cls.BASIC_QA, cls.PROJECT_DEEP, cls.SUMMARY]


class InterviewStateMachine:
    """
    面试流程状态机（增强版）

    职责：
    1. 维护当前面试阶段
    2. 统计每个阶段已问的问题数
    3. 判断是否需要跳转到下一阶段
    4. 提供当前阶段对应的增强版指令（含策略）
    5. 支持动态调整阶段参数
    """

    def __init__(
        self,
        resume_data: dict,
        position: str,
        max_questions: Optional[dict] = None,
    ):
        self.resume_data = resume_data
        self.position = position
        self.stage = InterviewStage.OPENING
        self.max_questions = max_questions or DEFAULT_MAX_QUESTIONS

        # 每个阶段已问的问题计数
        self.question_count: Dict[str, int] = {
            s.value: 0 for s in InterviewStage.ordered()
        }

        # 阶段切换历史（便于追溯）
        self.transition_history: list = []

    # ---- 公开方法 ----

    @property
    def is_finished(self) -> bool:
        return self.stage == InterviewStage.FINISHED

    def record_question(self):
        """记录当前阶段多问了一个问题"""
        if self.stage != InterviewStage.FINISHED:
            self.question_count[self.stage.value] += 1

    def should_transition(self) -> bool:
        """判断当前阶段是否应该跳转（由外部标记触发，不再自动判断）"""
        return False  # 不再自动切换，由 AI 输出标记控制

    def force_advance(self) -> InterviewStage:
        """强制推进到下一阶段（由路由器触发）"""
        old_stage = self.stage
        new_stage = self.next_stage()
        self.transition_history.append({
            "from": old_stage.value,
            "to": new_stage.value,
            "questions_asked": self.question_count.get(old_stage.value, 0),
        })
        return new_stage

    def next_stage(self) -> InterviewStage:
        """跳转到下一个阶段，并返回新阶段"""
        stages = InterviewStage.ordered()
        try:
            idx = stages.index(self.stage)
        except ValueError:
            self.stage = InterviewStage.FINISHED
            return self.stage

        if idx + 1 < len(stages):
            self.stage = stages[idx + 1]
        else:
            self.stage = InterviewStage.FINISHED
        return self.stage

    def try_advance(self) -> InterviewStage:
        """自动检查并推进阶段，返回当前（可能已更新的）阶段"""
        if self.should_transition():
            self.next_stage()
        return self.stage

    def get_stage_instruction(self) -> str:
        """
        根据当前阶段返回给 LLM 的增强版额外指令

        借鉴闲鱼Agent的prompt设计：
        - 明确的角色设定
        - 详细的策略指导
        - 具体的行为约束
        - 语言风格要求
        """
        instructions = {
            InterviewStage.OPENING: (
                "【当前阶段】自我介绍阶段\n\n"
                "【角色策略】你是一位和蔼的面试官，正在暖场。你的目标是让候选人放松下来。\n\n"
                "【行为规则】\n"
                "1. 如果是面试刚开始（对话历史为空），用一句话打招呼并请候选人自我介绍\n"
                "2. 打招呼示例：'你好，欢迎来参加面试！请先简单介绍一下自己吧。'\n"
                "3. 如果候选人已介绍，做简短回应即可\n"
                "4. 如果候选人只说了姓名学校，追问：'能简单说说你的专业方向和兴趣吗？'\n\n"
                "【允许话题】姓名、学校、专业、学历、兴趣方向\n"
                "【禁止话题】技术细节、项目实现、算法原理、八股文\n\n"
                "【语言风格】口语化、简短、≤50字。像真人面试官聊天，不要书面语。\n\n"
                "【极其重要的提醒】\n"
                "- 你是面试官！你不需要自我介绍！如果你发现自己在说'我叫xx'、'我毕业于xx'，说明你搞错了身份！\n"
                "- 第一句话不要说过渡语，要先听候选人介绍\n\n"
                "【过渡触发】当候选人介绍了姓名+背景+方向后，回应并说：\n"
                "'好的，感谢你的介绍！接下来我们进入编程环节，请看下方的算法题，完成后点击提交。'"
            ),
            InterviewStage.CODING: (
                "【当前阶段】编程考察阶段\n\n"
                "【角色策略】你是一位严谨的技术面试官，等待候选人提交代码后进行专业点评。\n\n"
                "【行为规则】\n"
                "1. 如果候选人尚未提交代码（消息中无【代码提交】标记），提醒：'请在下方代码编辑器中完成算法题后提交'\n"
                "2. 如果候选人提交了代码，从三个维度点评：\n"
                "   - 正确性：逻辑是否正确，边界情况处理\n"
                "   - 效率：时间/空间复杂度分析\n"
                "   - 代码风格：命名规范、可读性\n"
                "3. 点评后追问：'你能分析一下这个解法的时间复杂度吗？有没有优化思路？'\n\n"
                "【允许话题】当前算法题、代码实现、复杂度、优化思路\n"
                "【禁止话题】八股文、项目经历、其他技术概念\n\n"
                "【语言风格】专业、具体，指出优缺点。点评≤100字。\n\n"
                "【过渡触发】代码讨论充分后说：\n"
                "'好的，编程环节到此结束。接下来我们进入基础知识考察，我会问你一些技术问题。'"
            ),
            InterviewStage.BASIC_QA: (
                "【当前阶段】基础知识考察阶段\n\n"
                "【角色策略】你是一位经验丰富的技术面试官，擅长通过层层追问考察候选人的技术深度。\n\n"
                "【核心策略】（借鉴梯度追问法）\n"
                "1. 第一个问题：从候选人简历中最擅长的技术栈出发，问一个中等难度的基础问题\n"
                "2. 如果回答好：追问更深入的细节或原理\n"
                "3. 如果回答不好：换一个方向，给候选人展示其他技能的机会\n"
                "4. 每次只问一个问题！等候选人回答后再继续\n\n"
                "【问题方向】\n"
                "- 算法与数据结构：时间复杂度、常见算法思想\n"
                "- 编程语言特性：内存管理、多线程、异步\n"
                "- 系统知识：进程线程、网络协议、数据库\n"
                "- AI/ML：模型原理、训练技巧（如适用）\n\n"
                "【允许话题】技术概念、原理解释、框架对比\n"
                "【禁止话题】候选人具体项目的实现细节\n\n"
                "【语言风格】问题清晰明确，回应简短。≤80字。\n\n"
                "【过渡触发】问完2-3个问题后说：\n"
                "'基础知识部分就先到这里。接下来我想了解一下你的项目经历。'"
            ),
            InterviewStage.PROJECT_DEEP: (
                "【当前阶段】项目深挖阶段\n\n"
                "【角色策略】你是一位对技术细节有强烈好奇心的面试官，用 STAR 法则层层追问。\n\n"
                "【核心策略】（STAR追问法）\n"
                "1. Situation：先了解项目背景和规模\n"
                "2. Task：候选人在项目中的具体职责\n"
                "3. Action：技术选型原因、遇到的挑战、如何解决\n"
                "4. Result：最终成效、学到了什么\n\n"
                "【追问技巧】\n"
                "- '你在这个项目中具体负责哪部分？'\n"
                "- '选择这个技术方案的原因是什么？有考虑过其他方案吗？'\n"
                "- '遇到的最大挑战是什么？你是怎么解决的？'\n"
                "- '如果让你重做，有什么地方会做不同的选择？'\n\n"
                "【允许话题】项目背景、技术选型、挑战与解决方案、个人贡献\n"
                "【禁止话题】与候选人项目无关的通用技术问题\n\n"
                "【语言风格】表现出兴趣，追问有针对性。≤60字。\n\n"
                "【过渡触发】深入讨论1-2个项目后说：\n"
                "'项目部分聊得差不多了，我们进入最后的总结环节。'"
            ),
            InterviewStage.SUMMARY: (
                "【当前阶段】总结阶段\n\n"
                "【角色策略】你是一位温和的面试官，正在礼貌地结束面试。\n\n"
                "【行为规则】\n"
                "1. 先简单总结面试感受（一句话即可）\n"
                "2. 询问候选人是否有问题想问\n"
                "3. 如果候选人有问题，耐心回答\n"
                "4. 最后温暖告别\n\n"
                "【禁止】不能再提新的技术问题\n\n"
                "【语言风格】友好、温暖。≤60字。\n\n"
                "【过渡触发】候选人没有问题或回答完后说：\n"
                "'好的，今天的面试就到这里，感谢你的参与！后续结果我们会尽快通知你，祝你一切顺利！'"
            ),
            InterviewStage.FINISHED: "",
        }
        return instructions.get(self.stage, "")

    def to_dict(self) -> dict:
        """序列化为字典（方便存入数据库或返回前端）"""
        return {
            "current_stage": self.stage.value,
            "question_count": self.question_count,
            "is_finished": self.is_finished,
            "transition_history": self.transition_history,
        }
