import { useEffect, useState } from "react";
import { api } from "../api/client";
import { DriveFile } from "../types";

export function SellerDrive() {
    const [files, setFiles] = useState<DriveFile[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [errorMSG, setErrorMSG] = useState("");

    const fetchFiles = async () => {
        try {
            const data = await api.get<DriveFile[]>("/drive");
            setFiles(data);
        } catch (err: any) {
            setErrorMSG(err.message || "Failed to load files");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchFiles();
    }, []);

    const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        if (file.type !== "application/pdf") {
            setErrorMSG("Only PDF files are allowed.");
            e.target.value = "";
            return;
        }

        setUploading(true);
        setErrorMSG("");

        const formData = new FormData();
        formData.append("file", file);

        try {
            const token = localStorage.getItem("mercury_token");
            const res = await fetch("http://localhost:8005/api/drive/upload", {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
                body: formData,
            });

            if (!res.ok) {
                throw new Error("Failed to upload file");
            }

            await fetchFiles();
        } catch (err: any) {
            setErrorMSG(err.message || "Failed to upload file");
        } finally {
            setUploading(false);
            e.target.value = ""; // Reset input
        }
    };

    const handleDelete = async (id: number) => {
        if (!confirm("Are you sure you want to delete this file?")) return;
        try {
            await api.delete(`/drive/${id}`);
            setFiles((prev) => prev.filter((f) => f.id !== id));
        } catch (err: any) {
            setErrorMSG(err.message || "Failed to delete file");
        }
    };

    const handleDownload = (id: number, e: React.MouseEvent) => {
        e.preventDefault();
        const token = localStorage.getItem("mercury_token");
        window.open(`http://localhost:8005/api/drive/${id}/download?token=${token}`, "_blank");
    };

    return (
        <div className="page">
            <div className="page-header">
                <h1 className="page-title">Seller Drive</h1>
                <div>
                    <input
                        type="file"
                        id="file-upload"
                        accept=".pdf,application/pdf"
                        style={{ display: "none" }}
                        onChange={handleUpload}
                        disabled={uploading}
                    />
                    <label htmlFor="file-upload" className="btn btn-primary" style={{ cursor: "pointer" }}>
                        {uploading ? "Uploading..." : "Upload File"}
                    </label>
                </div>
            </div>

            {errorMSG && <div className="alert alert-error" style={{ marginBottom: "20px" }}>{errorMSG}</div>}

            {loading ? (
                <div className="loading-state">Loading files...</div>
            ) : files.length === 0 ? (
                <div className="empty-state">
                    <p>Your drive is empty. Upload files to manage them here.</p>
                </div>
            ) : (
                <div className="table-container">
                    <table className="table" style={{ width: "100%", textAlign: "left", borderCollapse: "collapse" }}>
                        <thead>
                            <tr style={{ borderBottom: "1px solid #ccc" }}>
                                <th style={{ padding: "10px" }}>File Name</th>
                                <th style={{ padding: "10px" }}>Size</th>
                                <th style={{ padding: "10px" }}>Uploaded At</th>
                                <th style={{ padding: "10px", textAlign: "right" }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {files.map((file) => (
                                <tr key={file.id} style={{ borderBottom: "1px solid #eee" }}>
                                    <td style={{ padding: "10px" }}>{file.file_name}</td>
                                    <td style={{ padding: "10px" }}>{(file.size / 1024).toFixed(2)} KB</td>
                                    <td style={{ padding: "10px" }}>{new Date(file.created_at).toLocaleString()}</td>
                                    <td style={{ padding: "10px", textAlign: "right", gap: "10px", display: "flex", justifyContent: "flex-end" }}>
                                        <button className="btn btn-sm btn-secondary" onClick={(e) => handleDownload(file.id, e)}>Download</button>
                                        <button className="btn btn-sm btn-secondary" style={{ backgroundColor: "#ef4444", color: "white", border: "none" }} onClick={() => handleDelete(file.id)}>Delete</button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
