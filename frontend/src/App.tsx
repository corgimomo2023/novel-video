import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from './components/AppLayout'
import { LoadingScreen } from './components/Page'
import { useAuth } from './contexts/AuthContext'
import { DashboardPage } from './pages/DashboardPage'
import { GPUPage } from './pages/GPUPage'
import { JobsPage } from './pages/JobsPage'
import { LoginPage } from './pages/LoginPage'
import { ProjectDetailPage } from './pages/ProjectDetailPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { SettingsPage } from './pages/SettingsPage'

export default function App(){const{user,loading}=useAuth();if(loading)return <LoadingScreen/>;if(!user)return <LoginPage/>;return <AppLayout><Routes><Route path="/" element={<DashboardPage/>}/><Route path="/projects" element={<ProjectsPage/>}/><Route path="/projects/:id" element={<ProjectDetailPage/>}/><Route path="/jobs" element={<JobsPage/>}/><Route path="/gpu" element={<GPUPage/>}/><Route path="/settings" element={<SettingsPage/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Routes></AppLayout>}
