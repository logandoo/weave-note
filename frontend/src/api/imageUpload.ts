import apiClient from './client'

const createdObjectUrls = new Set<string>()

export interface ImageUploadResult {
  path: string
  filename: string
  size: number
}

export async function uploadImage(file: File): Promise<ImageUploadResult> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await apiClient.post('/images/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function uploadMedia(file: File): Promise<ImageUploadResult> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await apiClient.post('/images/upload-media', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

function trackObjectUrl(url: string): string {
  createdObjectUrls.add(url)
  return url
}

export function revokeImageObjectUrl(url: string) {
  if (createdObjectUrls.has(url)) {
    URL.revokeObjectURL(url)
    createdObjectUrls.delete(url)
  }
}

export async function resolveImageUrl(path: string): Promise<string> {
  if (path.startsWith('blob:') || path.startsWith('data:')) return path
  if (path.startsWith('http://') || path.startsWith('https://')) return path
  try {
    // 兼容旧构建存下的 /api/files/download?path=... 签名 URL：剥离为纯 path 再走
    // /images/serve（真实端点，Bearer header 认证）。
    if (path.startsWith('/api/files/download')) {
      const u = new URL(path, window.location.origin)
      path = u.searchParams.get('path') || path
    }
    const res = await apiClient.get('/images/serve', {
      params: { path },
      responseType: 'blob',
    })
    return trackObjectUrl(URL.createObjectURL(res.data))
  } catch {
    return path
  }
}
