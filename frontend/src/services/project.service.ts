import { api } from './api'
import type { Project, CreateProjectRequest, UpdateProjectRequest, ExecCommandRequest, ExecCommandResponse } from '@/types/project.types'

export const getProjectsAPI = async (): Promise<{ total: number; projects: Project[] }> => {
  const response = await api.get('/api/v1/projects')
  return response.data
}

export const getProjectAPI = async (id: string): Promise<Project> => {
  const response = await api.get(`/api/v1/projects/${id}`)
  return response.data
}

export const createProjectAPI = async (data: CreateProjectRequest): Promise<Project> => {
  const response = await api.post('/api/v1/projects', data)
  return response.data
}

export const updateProjectAPI = async (id: string, data: UpdateProjectRequest): Promise<Project> => {
  const response = await api.put(`/api/v1/projects/${id}`, data)
  return response.data
}

export const provisionProjectAPI = async (id: string) => {
  const response = await api.post(`/api/v1/projects/${id}/provision`)
  return response.data
}

export const execCommandAPI = async (id: string, data: ExecCommandRequest): Promise<ExecCommandResponse> => {
  const response = await api.post(`/api/v1/projects/${id}/exec`, data)
  return response.data
}

export const stopProjectAPI = async (id: string): Promise<Project> => {
  const response = await api.post(`/api/v1/projects/${id}/stop`)
  return response.data
}

export const deleteProjectAPI = async (id: string): Promise<void> => {
  await api.delete(`/api/v1/projects/${id}`)
}

export const reprovisionProjectAPI = async (id: string): Promise<Project> => {
  const response = await api.post(`/api/v1/projects/${id}/reprovision`)
  return response.data
}
