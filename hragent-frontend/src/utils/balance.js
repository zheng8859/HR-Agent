// 评分维度分值配平计算（与后端 validate_balance 语义一致：sum(max_score) vs total_score）。

/**
 * 维度分值之和。以 max_score 为准（后端配平校验字段），缺失时回退 weight。
 * @param {Array<{name:string, weight:number, max_score:number, description:string}>} dimensions
 */
export function sumScores(dimensions) {
  return dimensions.reduce((acc, d) => {
    const v = Number(d?.max_score ?? d?.weight ?? 0)
    return acc + (Number.isFinite(v) ? v : 0)
  }, 0)
}

/**
 * 配平校验：返回是否配平、分值和、与总分的差值（不自动修正）。
 * @param {Array} dimensions 评分维度
 * @param {number} totalScore 总分，默认 100
 */
export function checkBalance(dimensions, totalScore = 100) {
  const scoreSum = sumScores(dimensions)
  const difference = totalScore - scoreSum
  return {
    isBalanced: Math.abs(difference) < 1e-9,
    scoreSum,
    difference,
  }
}
