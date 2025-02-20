'use client'

import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { useRouter } from "next/navigation"

export default function DashboardPage() {
  const router = useRouter()

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card className="p-4">
          <h2 className="text-xl font-semibold mb-4">Photo Section</h2>
          <p className="text-gray-600 mb-4">View and manage your photos</p>
          <Button 
            onClick={() => router.push('/dashboard/photo')}
            className="w-full"
          >
            Go to Photos
          </Button>
        </Card>

        <Card className="p-4">
          <h2 className="text-xl font-semibold mb-4">Video Section</h2>
          <p className="text-gray-600 mb-4">View and manage your videos</p>
          <Button 
            onClick={() => router.push('/dashboard/video')}
            className="w-full"
          >
            Go to Videos
          </Button>
        </Card>

        <Card className="p-4">
          <h2 className="text-xl font-semibold mb-4">Live Section</h2>
          <p className="text-gray-600 mb-4">Start or join live sessions</p>
          <Button 
            onClick={() => router.push('/dashboard/live')}
            className="w-full"
          >
            Go to Live
          </Button>
        </Card>
      </div>
    </div>
  )
}
