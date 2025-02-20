"use client"

import { useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface DetectionResult {
  predicted_class: string
  confidence: number
  class_probabilities: {
    [key: string]: number
  }
}

export default function LiveDetection() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  
  const [isStreaming, setIsStreaming] = useState(false)
  const [result, setResult] = useState<DetectionResult | null>(null)
  const [error, setError] = useState<string>("")

  const startWebcam = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          width: 640,
          height: 480,
          facingMode: "environment" // Prefer back camera if available
        } 
      })
      
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        streamRef.current = stream
      }
      
      setIsStreaming(true)
      setError("")
      connectWebSocket()
    } catch (err) {
      setError("Failed to access camera. Please ensure you have granted permission.")
      console.error("Error accessing webcam:", err)
    }
  }

  const stopWebcam = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(track => track.stop())
    }
    if (wsRef.current) {
      wsRef.current.close()
    }
    setIsStreaming(false)
    setResult(null)
  }

  const connectWebSocket = () => {
    wsRef.current = new WebSocket('ws://localhost:8000/predict/live')
    
    wsRef.current.onopen = () => {
      console.log('WebSocket Connected')
      startVideoProcessing()
    }
    
    wsRef.current.onclose = () => {
      console.log('WebSocket Disconnected')
      stopWebcam()
    }
    
    wsRef.current.onerror = (error) => {
      console.error('WebSocket Error:', error)
      setError("Connection error. Please try again.")
      stopWebcam()
    }
    
    wsRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setResult(data)
    }
  }

  const startVideoProcessing = () => {
    const processFrame = () => {
      if (!isStreaming || !canvasRef.current || !videoRef.current || !wsRef.current) return
      
      const context = canvasRef.current.getContext('2d')
      if (!context) return
      
      // Draw the video frame to the canvas
      context.drawImage(videoRef.current, 0, 0, 640, 480)
      
      // Convert the frame to base64 and send to websocket
      const imageData = canvasRef.current.toDataURL('image/jpeg', 0.5)
      wsRef.current.send(imageData)
      
      // Schedule the next frame
      requestAnimationFrame(processFrame)
    }

    requestAnimationFrame(processFrame)
  }

  useEffect(() => {
    return () => {
      stopWebcam()
    }
  }, [])

  return (
    <div className="space-y-6 max-w-2xl mx-auto p-4">
      <Card className="p-4">
        <CardHeader>
          <CardTitle className="text-center text-xl">Live Detection</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="aspect-video relative bg-gray-100 rounded-lg overflow-hidden">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover"
            />
            <canvas
              ref={canvasRef}
              width={640}
              height={480}
              className="hidden"
            />
            {!isStreaming && !error && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-900/10">
                <p className="text-gray-600">Camera feed will appear here</p>
              </div>
            )}
            {error && (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-900/10">
                <p className="text-red-600">{error}</p>
              </div>
            )}
          </div>

          <Button
            onClick={isStreaming ? stopWebcam : startWebcam}
            className="w-full"
          >
            {isStreaming ? "Stop Camera" : "Start Camera"}
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card className="p-4">
          <CardHeader>
            <CardTitle className="text-center text-lg">Live Results</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-center">
              <p className="text-2xl font-bold text-primary">
                {result.predicted_class}
              </p>
              <p className="text-lg">
                Confidence: {(result.confidence * 100).toFixed(2)}%
              </p>
            </div>

            <div className="space-y-2">
              <p className="font-medium">Class Probabilities:</p>
              {Object.entries(result.class_probabilities)
                .sort(([, a], [, b]) => b - a)
                .map(([className, probability]) => (
                  <div key={className} className="flex items-center gap-2">
                    <div className="w-full bg-gray-200 rounded-full h-2.5">
                      <div
                        className="bg-primary h-2.5 rounded-full transition-all duration-300"
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
