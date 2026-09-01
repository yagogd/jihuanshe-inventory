import React, { useState } from 'react'
import { api } from '../api.js'

export default function ItemImagePicker({ imagePath, onChange, onError }) {
  const [uploading, setUploading] = useState(false)

  async function selectImage(file) {
    if (!file) return
    setUploading(true)
    try {
      const data = await readBase64(file)
      const uploaded = await api.uploadImage({ filename: file.name, data })
      onChange(uploaded.image_path)
    } catch (error) {
      onError?.(error.message)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="item-image-picker">
      {imagePath ? (
        <img className="thumb" src={`/images/${imagePath}`} alt="Imagen de la carta" />
      ) : (
        <span className="item-image-placeholder">Sin imagen</span>
      )}
      <label className="item-image-button">
        {uploading ? 'Subiendo…' : imagePath ? 'Cambiar' : 'Añadir foto'}
        <input
          type="file"
          accept="image/*"
          disabled={uploading}
          onChange={(event) => selectImage(event.target.files?.[0])}
        />
      </label>
    </div>
  )
}

function readBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result).split(',')[1])
    reader.onerror = () => reject(new Error('No se pudo leer la imagen'))
    reader.readAsDataURL(file)
  })
}
