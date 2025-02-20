"use client"

import type React from "react"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import Image from "next/image"

interface DetectionResult {
  predicted_class: string
  confidence: number
  class_probabilities: {
    [key: string]: number
  }
}

export default function PhotoDetection() {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [result, setResult] = useState<DetectionResult | null>(null)
  const [loading, setLoading] = useState<boolean>(false)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFile = e.target.files[0]
      setFile(selectedFile)
      setPreview(URL.createObjectURL(selectedFile))
      setResult(null)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return
    
    setLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('http://localhost:8000/predict/image', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Failed to process image')
      }

      const data = await response.json()
      setResult(data)
    } catch (error) {
      console.error('Error:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-lg mx-auto p-4">
      <Card className="p-4">
        <CardHeader>
          <CardTitle className="text-center text-xl">Photo Detection</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4 flex flex-col items-center">
            <Input type="file" accept="image/*" onChange={handleFileChange} />
            {preview && (
              <div className="w-full flex justify-center">
                <Image
                  src={preview}
                  alt="Uploaded Preview"
                  width={300}
                  height={300}
                  className="rounded-lg shadow-md border border-gray-200"
                />
              </div>
            )}
            <Button type="submit" disabled={loading} className="w-full">
              {loading ? "Detecting..." : "Detect Objects"}
            </Button>
          </form>
        </CardContent>
      </Card>
      
      {result && (
        <Card className="p-4">
          <CardHeader>
            <CardTitle className="text-center text-lg">Detection Results</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-center">
              <p className="text-lg font-semibold">
                Detected: <span className="text-primary">{result.predicted_class}</span>
              </p>
              <p>
                Confidence: {(result.confidence * 100).toFixed(2)}%
              </p>
            </div>
            
            <div className="space-y-2">
              <p className="font-medium">Class Probabilities:</p>
              {Object.entries(result.class_probabilities).map(([className, probability]) => (
                <div key={className} className="flex items-center gap-2">
                  <div className="w-full bg-gray-200 rounded-full h-2.5">
                    <div
                      className="bg-primary h-2.5 rounded-full"
                      style={{ width: `${probability * 100}%` }}
                    />
                  </div>
                  <span className="min-w-[100px] text-sm">
                    {className}: {(probability * 100).toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
