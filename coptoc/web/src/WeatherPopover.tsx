import React from 'react'
import type { WeatherInfo } from './types'

interface Props {
  weather: WeatherInfo
  onClose: () => void
  style?: React.CSSProperties
}

export default function WeatherPopover({ weather, onClose, style }: Props) {
  const isSevere = weather.flight_category === 'IMC' || weather.active_advisories.some(a => a.severity === 'critical' || a.severity === 'elevated')
  const isMarginal = weather.flight_category === 'MVFR' || weather.active_advisories.length > 0

  return (
    <div className="weather-popover" style={style} onClick={e => e.stopPropagation()}>
      <div className="wp-head">
        <div className="wp-station-badge">{weather.station_id}</div>
        <div className="wp-head-info">
          <div className="wp-title">{weather.station_name}</div>
          <div className="wp-sub dim">Surface Observation & Tactical Aviation Forecast</div>
        </div>
        <button className="wp-close" onClick={onClose} title="Close Weather Inspector (Esc)">×</button>
      </div>

      <div className="wp-hero">
        <div className="wp-hero-main">
          <span className="wp-temp">{weather.temp_f}°<span className="dim">F</span> <span className="wp-temp-c dim">/ {weather.temp_c}°C</span></span>
          <span className="wp-cond">{weather.condition}</span>
        </div>
        <div className="wp-hero-chips">
          <span className={`chip wp-cat-chip ${weather.flight_category.toLowerCase()}`} title={weather.flight_category === 'VMC' ? 'Visual Meteorological Conditions' : weather.flight_category === 'MVFR' ? 'Marginal Visual Flight Rules' : 'Instrument Meteorological Conditions'}>
            {weather.flight_category}
          </span>
        </div>
      </div>

      <div className="wp-grid">
        <div className="wp-metric">
          <span className="wp-k">SURFACE WINDS</span>
          <span className="wp-v mono">
            {weather.wind_direction_deg}° at {weather.wind_speed_kt} KT
            {weather.wind_gust_kt ? <b className="wp-gust"> G{weather.wind_gust_kt}KT</b> : ''}
          </span>
        </div>
        <div className="wp-metric">
          <span className="wp-k">CLOUD CEILING</span>
          <span className="wp-v mono">{weather.ceiling_ft != null ? `${weather.ceiling_ft.toLocaleString()} FT AGL` : 'CLR / UNLIMITED'}</span>
        </div>
        <div className="wp-metric">
          <span className="wp-k">FLIGHT VISIBILITY</span>
          <span className="wp-v mono">{weather.visibility_sm >= 10 ? '10+ SM' : `${weather.visibility_sm} SM`}</span>
        </div>
        <div className="wp-metric">
          <span className="wp-k">ALTIMETER / BARO</span>
          <span className="wp-v mono">{weather.barometer_inhg.toFixed(2)} inHg</span>
        </div>
      </div>

      <div className={`wp-impact ${isSevere ? 'severe' : isMarginal ? 'marginal' : 'nominal'}`}>
        <div className="wp-impact-title">OPERATIONAL IMPACT · AIR & GROUND</div>
        <div className="wp-impact-desc">{weather.operational_impact}</div>
      </div>

      {weather.active_advisories.length > 0 && (
        <div className="wp-advisories">
          <div className="wp-k">ACTIVE WEATHER ADVISORIES ({weather.active_advisories.length})</div>
          <div className="wp-advisory-list">
            {weather.active_advisories.map(adv => (
              <div key={adv.id} className={`wp-adv-item ${adv.severity}`}>
                <div className="wp-adv-head">
                  <span className={`chip small ${adv.severity === 'critical' ? 'red' : adv.severity === 'elevated' ? 'red' : 'amber'}`}>
                    {adv.severity.toUpperCase()}
                  </span>
                  <span className="wp-adv-title">{adv.event}</span>
                  {adv.distance_km != null && <span className="dim small mono">{adv.distance_km} km</span>}
                </div>
                {adv.description && <div className="wp-adv-desc">{adv.description}</div>}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="wp-actions">
        <a href={weather.awc_url} target="_blank" rel="noreferrer" className="wp-link-btn" title="Open Aviation Weather Center METAR, TAF, and SIGMET charts">
          AVIATION WEATHER CENTER (AWC) ↗
        </a>
        <a href={weather.external_url} target="_blank" rel="noreferrer" className="wp-link-btn" title="Open NOAA National Weather Service detailed local forecast">
          NOAA / NWS FORECAST ↗
        </a>
      </div>
    </div>
  )
}
