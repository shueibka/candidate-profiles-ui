// frontend/src/NewJobPosting.js
import React, { useState } from "react";

function NewJobPosting() {
  const [form, setForm] = useState({
    title: "",
    department: "",
    locations: "",
    work_type: "",
    required_skills: "",
    preferred_skills: "",
    education_level: "",
    languages_required: "",
    experience_required: "",
    total_experience_years: "",
    responsibilities: "",
    qualifications: "",
    job_description: "",
  });

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await fetch("http://localhost:5000/job_postings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      alert("✅ Job posting created!");
      setForm({
        title: "",
        department: "",
        locations: "",
        work_type: "",
        required_skills: "",
        preferred_skills: "",
        education_level: "",
        languages_required: "",
        experience_required: "",
        total_experience_years: "",
        responsibilities: "",
        qualifications: "",
        job_description: "",
      });
    } catch (error) {
      console.error("Error creating job:", error);
      alert("❌ Failed to create job.");
    }
  };

  return (
    <div>
      <h2>Add New Job Posting</h2>
      <form onSubmit={handleSubmit} className="form">
        <input
          name="title"
          value={form.title}
          onChange={handleChange}
          placeholder="Title"
          required
        />
        <input
          name="department"
          value={form.department}
          onChange={handleChange}
          placeholder="Department"
        />
        <input
          name="locations"
          value={form.locations}
          onChange={handleChange}
          placeholder="Locations"
        />
        <input
          name="work_model"
          value={form.work_model}
          onChange={handleChange}
          placeholder="Work Model (e.g., Remote/Hybrid)"
        />
        <input
          name="required_skills"
          value={form.required_skills}
          onChange={handleChange}
          placeholder="Required Skills"
        />
        <input
          name="preferred_skills"
          value={form.preferred_skills}
          onChange={handleChange}
          placeholder="Preferred Skills"
        />
        <input
          name="education_level"
          value={form.education_level}
          onChange={handleChange}
          placeholder="Education Level"
        />
        <input
          name="languages_required"
          value={form.languages_required}
          onChange={handleChange}
          placeholder="Languages Required"
        />
        <input
          name="experience_required"
          value={form.experience_required}
          onChange={handleChange}
          placeholder="Experience Required"
        />
        <input
          name="total_experience_years"
          value={form.total_experience_years}
          onChange={handleChange}
          type="number"
          placeholder="Total Experience Years"
        />
        <textarea
          name="responsibilities"
          value={form.responsibilities}
          onChange={handleChange}
          placeholder="Responsibilities"
          rows="3"
        />
        <textarea
          name="qualifications"
          value={form.qualifications}
          onChange={handleChange}
          placeholder="Qualifications"
          rows="3"
        />
        <textarea
          name="job_description"
          value={form.job_description}
          onChange={handleChange}
          placeholder="Job Description"
          rows="5"
        />

        <button type="submit">Create Job</button>
      </form>
    </div>
  );
}

export default NewJobPosting;
