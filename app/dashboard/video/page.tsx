"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"

interface DetectionResult {
  predicted_class: string
  confidence: number
  frame_results: Array<{
    predicted_class: string
    confidence: number
    class_probabilities: {
      [key: string]: number
    }
  }>
}

export default function VideoDetection() {
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<DetectionResult | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [fileName, setFileName] = useState<string>("")

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0]
      setFile(selectedFile)
      setFileName(selectedFile.name)
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

      const response = await fetch('http://localhost:8000/predict/video', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Failed to process video')
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
          <CardTitle className="text-center text-xl">Video Detection</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Input 
                type="file" 
                accept="video/*"
                onChange={handleFileChange}
                className="cursor-pointer"
              />
              {fileName && (
                <p className="text-sm text-gray-500">
                  Selected: {fileName}
                </p>
              )}
            </div>
            
            <Button 
              type="submit" 
              disabled={loading || !file} 
              className="w-full"
            >
              {loading ? "Processing Video..." : "Detect Objects"}
            </Button>

            {loading && (
              <div className="space-y-2">
                <Progress value={33} />
                <p className="text-sm text-center text-gray-500">
                  Processing video frames...
                </p>
              </div>
            )}
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
                Dominant Class: <span className="text-primary">{result.predicted_class}</span>
              </p>
              <p>
                Overall Confidence: {(result.confidence * 100).toFixed(2)}%
              </p>
            </div>

            <div className="space-y-2">
              <p className="font-medium">Frame Analysis:</p>
              <div className="max-h-60 overflow-y-auto space-y-2 border rounded-lg p-2">
                {result.frame_results.map((frame, index) => (
                  <div key={index} className="p-2 bg-gray-50 rounded">
                    <p className="text-sm">
                      Frame {index + 1}: {frame.predicted_class} 
                      ({(frame.confidence * 100).toFixed(1)}%)
                    </p>
                    <div className="w-full bg-gray-200 rounded-full h-1.5 mt-1">
                      <div
                        className="bg-primary h-1.5 rounded-full"
                        style={{ width: `${frame.confidence * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <p className="font-medium">Statistics:</p>
              <div className="grid grid-cols-2 gap-2">
                <div className="bg-gray-50 p-2 rounded">
                  <p className="text-sm">Total Frames</p>
                  <p className="text-lg font-semibold">
                    {result.frame_results.length}
                  </p>
                </div>
                <div className="bg-gray-50 p-2 rounded">
                  <p className="text-sm">Avg. Confidence</p>
                  <p className="text-lg font-semibold">
                    {(result.frame_results.reduce((acc, curr) => acc + curr.confidence, 0) / 
                      result.frame_results.length * 100).toFixed(1)}%
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
