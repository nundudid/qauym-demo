import { Link, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import AdminRunsPage from './pages/AdminRunsPage';
import CommunitiesPage from './pages/CommunitiesPage';
import CommunityDetailPage from './pages/CommunityDetailPage';
import EditProfilePage from './pages/EditProfilePage';
import FeedPage from './pages/FeedPage';
import LoginPage from './pages/LoginPage';
import PeoplePage from './pages/PeoplePage';
import ProfilePage from './pages/ProfilePage';
import RegisterPage from './pages/RegisterPage';

function NotFound() {
  return (
    <>
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <p className="mt-2">
        <Link to="/" className="underline">
          Back to the feed
        </Link>
      </p>
    </>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      {/* Everything inside Layout requires a session. */}
      <Route element={<Layout />}>
        <Route index element={<FeedPage />} />
        <Route path="/u/:username" element={<ProfilePage />} />
        <Route path="/settings/profile" element={<EditProfilePage />} />
        <Route path="/people" element={<PeoplePage />} />
        <Route path="/communities" element={<CommunitiesPage />} />
        <Route path="/communities/:id" element={<CommunityDetailPage />} />
        <Route path="/admin/runs" element={<AdminRunsPage />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
