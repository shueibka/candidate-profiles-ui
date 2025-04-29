import React, { useEffect, useState } from "react";
import "./candidates.css";

function Candidates() {
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedCandidate, setSelectedCandidate] = useState(null);

  useEffect(() => {
    fetchCandidates();
  }, []);

  const fetchCandidates = async () => {
    try {
      const res = await fetch("http://localhost:5000/api/candidates");
      const data = await res.json();
      setCandidates(data);
    } catch (err) {
      console.error("Error fetching candidates:", err);
    } finally {
      setLoading(false);
    }
  };

  const openModal = (candidate = {}) => {
    setSelectedCandidate(candidate);
    setModalOpen(true);
  };

  const closeModal = () => {
    setSelectedCandidate(null);
    setModalOpen(false);
  };

  const handleChange = (e) => {
    setSelectedCandidate({
      ...selectedCandidate,
      [e.target.name]: e.target.value,
    });
  };

  const saveCandidate = async () => {
    try {
      const method = selectedCandidate?.record_id ? "PUT" : "POST";
      const url = selectedCandidate?.record_id
        ? `http://localhost:5000/api/candidates/${selectedCandidate.record_id}`
        : "http://localhost:5000/api/candidates";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(selectedCandidate),
      });

      if (!res.ok) throw new Error("Failed to save candidate");

      await fetchCandidates();
      closeModal();
    } catch (err) {
      console.error("Save failed:", err);
    }
  };

  const deleteCandidate = async (id) => {
    if (!window.confirm("Are you sure you want to delete this candidate?"))
      return;

    try {
      await fetch(`http://localhost:5000/api/candidates/${id}`, {
        method: "DELETE",
      });
      await fetchCandidates();
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  return (
    <div className="candidate-container">
      <h2>Candidates</h2>
      <button onClick={() => openModal()} className="add-button">
        ➕ Add Candidate
      </button>

      {loading ? (
        <p>Loading candidates...</p>
      ) : (
        <div className="card-grid">
          {candidates.map((c) => (
            <div key={c.record_id} className="candidate-card">
              <h3>{c.name}</h3>
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
              <div className="card-actions">
                <button onClick={() => openModal(c)}>✏️ Edit</button>
                <button onClick={() => deleteCandidate(c.record_id)}>
                  🗑️ Delete
                </button>
              </div>
              <a href={c.url} target="_blank" rel="noopener noreferrer">
                🔗 View Profile
              </a>
            </div>
          ))}
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
              value={selectedCandidate?.name || ""}
              onChange={handleChange}
              placeholder="Name"
            />
            <input
              name="city"
              value={selectedCandidate?.city || ""}
              onChange={handleChange}
              placeholder="City"
            />
            <input
              name="position"
              value={selectedCandidate?.position || ""}
              onChange={handleChange}
              placeholder="Position"
            />
            <input
              name="total_experience_years"
              type="number"
              value={selectedCandidate?.total_experience_years || ""}
              onChange={handleChange}
              placeholder="Experience (years)"
            />
            <input
              name="experiences"
              value={selectedCandidate?.experiences || ""}
              onChange={handleChange}
              placeholder="Skills"
            />
            <input
              name="url"
              value={selectedCandidate?.url || ""}
              onChange={handleChange}
              placeholder="Profile Link (URL)"
            />
            <div className="modal-actions">
              <button onClick={saveCandidate}>💾 Save</button>
              <button onClick={closeModal}>❌ Cancel</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Candidates;
