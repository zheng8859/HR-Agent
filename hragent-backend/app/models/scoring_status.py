"""评分标准状态枚举（代码枚举）。"""
import enum


class ScoringStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    archived = "archived"
