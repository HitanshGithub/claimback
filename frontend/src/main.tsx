import '@fontsource-variable/fraunces/opsz.css'
import '@fontsource-variable/fraunces/opsz-italic.css'
import '@fontsource-variable/inter/wght.css'
import './index.css'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router'
import { Layout } from './components/Layout'
import { ClaimPage } from './pages/ClaimPage'
import { ClaimsPage } from './pages/ClaimsPage'
import { HomePage } from './pages/HomePage'
import { NewClaimPage } from './pages/NewClaimPage'
import { NotFoundPage } from './pages/NotFoundPage'

const router = createBrowserRouter([
  {
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'new', element: <NewClaimPage /> },
      { path: 'claims', element: <ClaimsPage /> },
      { path: 'claims/:id', element: <ClaimPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
