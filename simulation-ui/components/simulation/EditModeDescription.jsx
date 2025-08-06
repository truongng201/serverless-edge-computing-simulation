import React from "react"

// EditModeDescription: Bottom instructions bar
export default function EditModeDescription({ description }) {
  return (
    <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 bg-black bg-opacity-75 text-white px-4 py-2 rounded-lg text-sm z-20">
      {description}
    </div>
  )
}
