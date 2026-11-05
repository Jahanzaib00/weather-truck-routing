import { levelInfo } from '../lib/risk.js'
import { fmtNum, fmtTime } from '../lib/format.js'

export default function CheckpointTable({ route, onFocus }) {
  return (
    <div className="cp-table-wrap">
      <table className="cp-table">
        <thead>
          <tr>
            <th>Mile</th>
            <th>ETA</th>
            <th title="Sustained wind (gust)">Wind</th>
            <th>Rain</th>
            <th>Snow</th>
            <th>Risk</th>
          </tr>
        </thead>
        <tbody>
          {route.checkpoints.map((c, i) => {
            const lv = levelInfo(c.level)
            return (
              <tr key={i} onClick={() => onFocus(i)} tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && onFocus(i)}>
                <td>{Math.round(c.mile)}</td>
                <td>{fmtTime(c.eta)}</td>
                <td>{fmtNum(c.wind_mph)}<small> ({fmtNum(c.gust_mph)})</small></td>
                <td>{fmtNum(c.rain_in, 2)}</td>
                <td>{fmtNum(c.snow_in, 2)}</td>
                <td><span className="pill" style={{ background: lv.color }} title={c.reasons.join('; ')}>{lv.name}</span></td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="hint">Wind in mph (gust), rain and snow in inches/hour at the truck's ETA. Click a row to show it on the map.</p>
    </div>
  )
}
