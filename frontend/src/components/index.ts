/**
 * 组件统一导出
 *
 * 用法: import { StatusBadge, Pagination, LoadingSpinner } from "@/components";
 */

// ---- 面试核心组件 ----
export { default as ChatInput } from "./ChatInput";
export { default as ChatMessage } from "./ChatMessage";
export { default as ChatWindow } from "./ChatWindow";
export { default as CodeEditor } from "./CodeEditor";
export { default as InterviewProgress } from "./InterviewProgress";
export { default as ResumeUploader } from "./ResumeUploader";
export { default as ReportCard } from "./ReportCard";

// ---- 布局 & 导航组件 ----
export {
  SidebarHeader,
  SidebarNavLink,
  SidebarDivider,
  SidebarFooter,
  SidebarNavGroup,
} from "./SidebarNav";

// ---- 通用 UI 组件 ----
export { default as StatCard } from "./StatCard";
export { default as StatusBadge } from "./StatusBadge";
export { default as Pagination } from "./Pagination";
export { default as CollapsibleSection } from "./CollapsibleSection";
export { default as ConversationReplay } from "./ConversationReplay";
export { default as LoadingSpinner } from "./LoadingSpinner";
