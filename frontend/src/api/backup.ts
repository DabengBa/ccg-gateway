import instance from './instance'

export interface WebdavSettings {
  url: string
  username: string
  password: string
}

export interface WebdavBackup {
  filename: string
  size: number
  modified: string
}

export const getWebdavSettings = () => instance.get<WebdavSettings>('/backup/webdav')

export const updateWebdavSettings = (data: Partial<WebdavSettings>) =>
  instance.put<WebdavSettings>('/backup/webdav', data)

export const testWebdavConnection = (data: WebdavSettings) =>
  instance.post<{ success: boolean }>('/backup/webdav/test', data)

export const exportToLocal = () =>
  instance.get('/backup/export/local', { responseType: 'blob' })

export const importFromLocal = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return instance.post('/backup/import/local', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

export const exportToWebdav = () =>
  instance.post<{ success: boolean; filename: string }>('/backup/export/webdav')

export const listWebdavBackups = () =>
  instance.get<{ backups: WebdavBackup[] }>('/backup/webdav/list')

export const importFromWebdav = (filename: string) =>
  instance.post('/backup/import/webdav', null, { params: { filename } })
