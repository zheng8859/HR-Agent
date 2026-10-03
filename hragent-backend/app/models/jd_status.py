"""JD 状态枚举（代码枚举，本期不落地 DB enum 类型）。"""
import enum


class JDStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"
