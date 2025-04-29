// frontend/src/App.js
import React from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import Candidates from "./candidates";
import JobPostings from "./jobPostings";
import "./App.css";

function App() {
  return (
    <Router>
      <div className="app-container">
        <header>
          <h1>Recruitment Portal</h1>
          <nav>
            <Link to="/">Candidates</Link> |{" "}
            <Link to="/jobs">Job Postings</Link>
          </nav>
        </header>

        <Routes>
          <Route path="/" element={<Candidates />} />
          <Route path="/jobs" element={<JobPostings />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
