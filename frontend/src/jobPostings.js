import React, { useEffect, useState } from "react";
import "./jobPostings.css";

function JobPostings() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedJob, setSelectedJob] = useState({
    title: "",
    department: "",
    locations: "",
    work_type: "",
    experience_required: "",
    total_experience_years: "",
    job_description: "",
  });

  useEffect(() => {
    fetchJobs();
  }, []);

  const fetchJobs = async () => {
    try {
      const res = await fetch("http://localhost:5000/api/job_postings");
      const data = await res.json();
      setJobs(data);
    } catch (error) {
      console.error("Failed to fetch jobs", error);
    } finally {
      setLoading(false);
    }
  };

  const openModal = (job = null) => {
    if (job) {
      setSelectedJob({ ...job });
    } else {
      setSelectedJob({
        title: "",
        department: "",
        locations: "",
        work_type: "",
        experience_required: "",
        total_experience_years: "",
        job_description: "",
      });
    }
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setSelectedJob((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const saveJob = async () => {
    try {
      const method = selectedJob?.id ? "PUT" : "POST";
      const url = selectedJob?.id
        ? `http://localhost:5000/job_postings/${selectedJob.id}`
        : "http://localhost:5000/job_postings";

      const res = await fetch(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(selectedJob),
      });

      if (!res.ok) {
        throw new Error("Failed to save job posting");
      }

      await fetchJobs();
      closeModal();
    } catch (error) {
      console.error("Save failed:", error);
    }
  };

  const deleteJob = async (jobId) => {
    if (!window.confirm("Are you sure you want to delete this job?")) return;

    try {
      await fetch(`http://localhost:5000/job_postings/${jobId}`, {
        method: "DELETE",
      });
      await fetchJobs();
    } catch (error) {
      console.error("Delete failed:", error);
    }
  };

  return (
    <div className="job-postings-container">
      <h2>Job Postings</h2>
      <button className="add-button" onClick={() => openModal()}>
        ➕ Add New Job
      </button>

      {loading ? (
        <p>Loading jobs...</p>
      ) : (
        <div className="job-cards">
          {jobs.map((job) => (
            <div className="job-card" key={job.id}>
              <h3>{job.title}</h3>
              <p>
                <strong>Department:</strong> {job.department}
              </p>
              <p>
                <strong>Location:</strong> {job.locations}
              </p>
              <p>
                <strong>Work Type:</strong> {job.work_type}
              </p>
              <p>
                <strong>Experience:</strong> {job.total_experience_years} years
              </p>
              <p>
                <strong>Description:</strong> {job.job_description}
              </p>
              <div className="card-actions">
                <button onClick={() => openModal(job)}>✏️ Edit</button>
                <button onClick={() => deleteJob(job.id)}>🗑️ Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}

      {modalOpen && (
        <div className="modal-overlay">
          <div className="modal">
            <h3>{selectedJob?.id ? "Edit Job" : "Create New Job"}</h3>

            <input
              name="title"
              value={selectedJob.title}
              onChange={handleChange}
              placeholder="Title"
            />
            <input
              name="department"
              value={selectedJob.department}
              onChange={handleChange}
              placeholder="Department"
            />
            <input
              name="locations"
              value={selectedJob.locations}
              onChange={handleChange}
              placeholder="Locations"
            />
            <input
              name="work_type"
              value={selectedJob.work_type}
              onChange={handleChange}
              placeholder="Work Type"
            />
            <input
              name="experience_required"
              value={selectedJob.experience_required}
              onChange={handleChange}
              placeholder="Experience Required"
            />
            <input
              type="number"
              name="total_experience_years"
              value={selectedJob.total_experience_years}
              onChange={handleChange}
              placeholder="Total Experience Years"
            />
            <textarea
              name="job_description"
              value={selectedJob.job_description}
              onChange={handleChange}
              placeholder="Job Description"
            ></textarea>

            <div className="modal-buttons">
              <button className="save-button" onClick={saveJob}>
                💾 Save
              </button>
              <button className="cancel-button" onClick={closeModal}>
                ❌ Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default JobPostings;
