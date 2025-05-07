import React, { useState, useEffect } from "react";
import "./candidates.css";

function Candidates() {
  const [candidates, setCandidates] = useState([]);
  const [search, setSearch] = useState("");
  const [sortOption, setSortOption] = useState("experience");
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [flipped, setFlipped] = useState({});
  const [loading, setLoading] = useState(true);
  const [jobModalOpen, setJobModalOpen] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [recommendationLoading, setRecommendationLoading] = useState(false);
  const [recommendationError, setRecommendationError] = useState(null);
  const [evaluation, setEvaluation] = useState(null);

  useEffect(() => {
    fetchCandidates();
  }, []);

  const fetchCandidates = async () => {
    setLoading(true);
    try {
      const res = await fetch("http://localhost:5000/api/candidates");
      const data = await res.json();
      setCandidates(data);
    } catch (error) {
      console.error("Failed to fetch candidates:", error);
    } finally {
      setLoading(false);
    }
  };

  const checkRecommendationStatus = async (taskId) => {
    let attempts = 0;
    while (attempts < 60) {
      try {
        const res = await fetch(
          `http://localhost:5000/api/recommendations/status/${taskId}`
        );
        if (!res.ok) throw new Error("Failed to fetch status");
        const data = await res.json();

        if (data.status === "complete") return data.results;
        if (data.status === "error") throw new Error(data.error);

        await new Promise((resolve) => setTimeout(resolve, 2000));
        attempts++;
      } catch (error) {
        console.error("Status check failed:", error);
        throw error;
      }
    }
    throw new Error("Processing timeout");
  };

  const fetchJobs = async () => {
    try {
      const res = await fetch("http://localhost:5000/api/job_postings");
      const data = await res.json();
      setJobs(data);
    } catch (error) {
      console.error("Failed to fetch jobs:", error);
    }
  };

  const getScoreDetails = (record_id) => {
    if (!Array.isArray(recommendations)) return null;
    return recommendations.find(
      (r) =>
        // try both keys
        r.candidate_id === record_id || r.id === record_id
    );
  };

  const openModal = (candidate) => {
    setSelectedCandidate(candidate || {});
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setSelectedCandidate(null);
  };

  const handleChange = (e) => {
    setSelectedCandidate({
      ...selectedCandidate,
      [e.target.name]: e.target.value,
    });
  };

  const saveCandidate = async () => {
    const method = selectedCandidate?.record_id ? "PUT" : "POST";
    const url = selectedCandidate?.record_id
      ? `http://localhost:5000/api/candidates/${selectedCandidate.record_id}`
      : `http://localhost:5000/api/candidates`;

    try {
      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(selectedCandidate),
      });
      if (!res.ok) throw new Error("Save failed");
      fetchCandidates();
      closeModal();
    } catch (error) {
      console.error("Error saving candidate:", error);
    }
  };

  const deleteCandidate = async (id) => {
    if (!window.confirm("Delete this candidate?")) return;
    try {
      await fetch(`http://localhost:5000/api/candidates/${id}`, {
        method: "DELETE",
      });
      fetchCandidates();
    } catch (error) {
      console.error("Error deleting candidate:", error);
    }
  };

  const filtered = candidates.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.city.toLowerCase().includes(search.toLowerCase())
  );

  const sorted = [...filtered].sort((a, b) => {
    const aScore = getScoreDetails(a.record_id)?.score || 0;
    const bScore = getScoreDetails(b.record_id)?.score || 0;

    if (recommendations.length > 0) return bScore - aScore;

    if (sortOption === "experience") {
      return b.total_experience_years - a.total_experience_years;
    } else if (sortOption === "name") {
      return a.name.localeCompare(b.name);
    } else if (sortOption === "city") {
      return a.city.localeCompare(b.city);
    }
    return 0;
  });

  const openJobModal = async () => {
    await fetchJobs();
    setJobModalOpen(true);
  };

  const handleJobSelect = async (jobId) => {
    try {
      setRecommendationError(null);
      setRecommendationLoading(true);

      const startRes = await fetch(
        `http://localhost:5000/api/recommendations/${jobId}`
      );

      if (!startRes.ok) {
        const errorData = await startRes.json();
        throw new Error(errorData.error || "Recommendation failed");
      }

      const { task_id } = await startRes.json();
      const results = await checkRecommendationStatus(task_id);
      const { candidates, evaluation } = results || {};

      if (!Array.isArray(candidates) || candidates.length === 0) {
        setRecommendationError(
          "No qualified candidates found matching domain requirements"
        );
      }

      setRecommendations(candidates);
      setEvaluation(evaluation);
    } catch (error) {
      setRecommendationError(error.message);
    } finally {
      setRecommendationLoading(false);
    }
  };

  const renderCandidateCard = (c) => {
    const isFlipped = flipped[c.record_id] || false;
    const scoreData = getScoreDetails(c.record_id);
    const score = scoreData?.score || null;
    const hasValidAbout = c.about?.split(/\s+/).length >= 25;
    const hasValidSkills = c.experiences?.split(",").length >= 2;

    return (
      <div key={c.record_id} className="candidate-card">
        {(!hasValidAbout || !hasValidSkills) && (
          <div className="profile-warning">
            ⚠️ {!hasValidAbout && "About "}
            {!hasValidAbout && !hasValidSkills && "& "}
            {!hasValidSkills && "Skills"}
          </div>
        )}

        {score !== null && (
          <div
            className={`score-circle ${
              score < 50
                ? "low-score"
                : score < 75
                ? "medium-score"
                : "high-score"
            }`}
          >
            {Math.round(score)}%
          </div>
        )}

        <div
          className={`card-inner ${isFlipped ? "flipped" : ""}`}
          onClick={() =>
            setFlipped((f) => ({ ...f, [c.record_id]: !f[c.record_id] }))
          }
        >
          <div className="card-front">
            <h3>{c.name}</h3>
            <div className="domain-tag">
              <strong>Domain:</strong> {c.domain || "Not detected"}
            </div>
            <p>
              <strong>Position:</strong> {c.position}
            </p>
            <p>
              <strong>City:</strong> {c.city}
            </p>
            <p>
              <strong>Experience:</strong> {c.total_experience_years} years
            </p>
            <p>
              <strong>Skills:</strong> {c.experiences}
            </p>
            <a href={c.url} target="_blank" rel="noreferrer">
              View Profile
            </a>
            <div className="card-actions">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  openModal(c);
                }}
              >
                ✏️ Edit
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  deleteCandidate(c.record_id);
                }}
              >
                🗑️ Delete
              </button>
            </div>
          </div>

          <div className="card-back">
            <h4>📊 Recommendation Details</h4>
            {scoreData ? (
              <>
                <p>
                  <strong>Match Score:</strong> {score}%
                </p>
                <table className="evaluation-table">
                  <tbody>
                    <tr>
                      <td>Precision</td>
                      <td>{scoreData.precision?.toFixed(2) || "N/A"}</td>
                    </tr>
                    <tr>
                      <td>Recall</td>
                      <td>{scoreData.recall?.toFixed(2) || "N/A"}</td>
                    </tr>
                    <tr>
                      <td>F1 Score</td>
                      <td>{scoreData.f1_score?.toFixed(2) || "N/A"}</td>
                    </tr>
                  </tbody>
                </table>
              </>
            ) : (
              <p>
                No recommendation available. Ensure profile has complete About
                section (25+ words) and Skills.
              </p>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="candidates-container">
      {recommendationLoading && (
        <div className="loading-overlay">
          <p>Generating recommendations... This may take a minute.</p>
        </div>
      )}

      {recommendationError && (
        <div className="error-message">Error: {recommendationError}</div>
      )}

      {evaluation && (
        <div className="evaluation-summary">
          <p>
            📊 <strong>Average Score:</strong> {evaluation.average_score}
          </p>
          <p>
            ✅ <strong>Candidates Above 50%:</strong>{" "}
            {evaluation.above_50_count}
          </p>
          <p>
            👥 <strong>Total Evaluated:</strong> {evaluation.total_candidates}
          </p>
        </div>
      )}

      <h2>
        Candidates{" "}
        <span
          style={{ cursor: "pointer", fontSize: "20px" }}
          title="Trigger Recommendations"
          onClick={openJobModal}
        >
          ⚙️
        </span>
      </h2>

      <div className="toolbar">
        <input
          type="text"
          placeholder="Search by name or city."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          value={sortOption}
          onChange={(e) => setSortOption(e.target.value)}
        >
          <option value="experience">Experience (Descending)</option>
          <option value="name">Name (A-Z)</option>
          <option value="city">City (A-Z)</option>
        </select>
        <button onClick={() => openModal({})}>➕ Add Candidate</button>
      </div>

      {loading ? (
        <p>Loading candidates...</p>
      ) : (
        <div className="candidate-cards">
          {sorted.map((c) => renderCandidateCard(c))}
        </div>
      )}

      {modalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>
              {selectedCandidate?.record_id
                ? "Edit Candidate"
                : "New Candidate"}
            </h3>
            <input
              name="name"
              value={selectedCandidate.name || ""}
              onChange={handleChange}
              placeholder="Name"
            />
            <input
              name="position"
              value={selectedCandidate.position || ""}
              onChange={handleChange}
              placeholder="Position"
            />
            <input
              name="city"
              value={selectedCandidate.city || ""}
              onChange={handleChange}
              placeholder="City"
            />
            <input
              name="total_experience_years"
              type="number"
              value={selectedCandidate.total_experience_years || ""}
              onChange={handleChange}
              placeholder="Experience (years)"
            />
            <textarea
              name="experiences"
              value={selectedCandidate.experiences || ""}
              onChange={handleChange}
              placeholder="Skills (comma-separated)"
            />
            <input
              name="url"
              value={selectedCandidate.url || ""}
              onChange={handleChange}
              placeholder="Profile URL"
            />
            <div className="modal-actions">
              <button onClick={saveCandidate}>💾 Save</button>
              <button onClick={closeModal}>❌ Cancel</button>
            </div>
          </div>
        </div>
      )}

      {jobModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Choose Job for Recommendation</h3>
            <ul style={{ maxHeight: "200px", overflowY: "auto", padding: 0 }}>
              {jobs.map((job) => (
                <li
                  key={job.id}
                  style={{ cursor: "pointer", padding: "8px 0" }}
                  onClick={() => handleJobSelect(job.id)}
                >
                  {job.title}
                </li>
              ))}
            </ul>
            <div className="modal-actions">
              <button onClick={() => setJobModalOpen(false)}>❌ Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Candidates;
