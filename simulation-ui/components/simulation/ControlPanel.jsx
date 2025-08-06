import React from "react"

// ControlPanel: Left side panel with all controls/settings
export default function ControlPanel(props) {
  return (
    <div className={`absolute left-0 top-0 h-full bg-white shadow-lg transition-transform duration-300 ${props.leftPanelOpen ? "translate-x-0" : "-translate-x-80"} w-80 z-10`}>
      <div className="p-4 h-full overflow-y-auto">
        {props.children}
      </div>
    </div>
  )
}
