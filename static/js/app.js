// Main JavaScript for Face Recognition Attendance System

// Global variables
let currentSessionId = null;
let cameraStream = null;

// Utility Functions
function showAlert(message, type = "info") {
  const alertClass = type === "error" ? "danger" : type;
  const alertHtml = `
        <div class="alert alert-${alertClass} alert-dismissible fade show" role="alert">
            <i class="fas fa-${getAlertIcon(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

  // Find container and insert alert
  const container = document.querySelector(".container-fluid") || document.body;
  const tempDiv = document.createElement("div");
  tempDiv.innerHTML = alertHtml;
  container.insertBefore(tempDiv.firstElementChild, container.firstElementChild);

  // Auto dismiss after 5 seconds
  setTimeout(() => {
    const alert = container.querySelector(".alert");
    if (alert) {
      alert.remove();
    }
  }, 5000);
}

function getAlertIcon(type) {
  const icons = {
    success: "check-circle",
    error: "exclamation-triangle",
    warning: "exclamation-circle",
    info: "info-circle",
  };
  return icons[type] || "info-circle";
}

// Format date and time
function formatDateTime(dateTime) {
  const date = new Date(dateTime);
  return date.toLocaleString("vi-VN");
}

function formatDate(date) {
  const d = new Date(date);
  return d.toLocaleDateString("vi-VN");
}

function formatTime(time) {
  const [hour, minute] = time.split(":");
  return `${hour}:${minute}`;
}

// Image preview for file uploads
function previewImage(input, previewId) {
  const file = input.files[0];
  const preview = document.getElementById(previewId);

  if (file) {
    const reader = new FileReader();
    reader.onload = function (e) {
      preview.src = e.target.result;
      preview.style.display = "block";
    };
    reader.readAsDataURL(file);
  }
}

// Form validation
function validateForm(formId) {
  const form = document.getElementById(formId);
  const inputs = form.querySelectorAll("input[required], select[required], textarea[required]");
  let isValid = true;

  inputs.forEach((input) => {
    if (!input.value.trim()) {
      input.classList.add("is-invalid");
      isValid = false;
    } else {
      input.classList.remove("is-invalid");
    }
  });

  return isValid;
}

// AJAX Functions
async function apiRequest(url, options = {}) {
  try {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("API request failed:", error);
    throw error;
  }
}

// Load data for select elements
async function loadClasses(selectId) {
  try {
    const classes = await apiRequest("/classes/api/list");
    const select = document.getElementById(selectId);

    if (select) {
      select.innerHTML = '<option value="">-- Chọn lớp học --</option>';
      classes.forEach((cls) => {
        const option = document.createElement("option");
        option.value = cls.id;
        option.textContent = `${cls.class_code} - ${cls.class_name}`;
        select.appendChild(option);
      });
    }
  } catch (error) {
    showAlert("Lỗi khi tải danh sách lớp học", "error");
  }
}

async function loadSubjects(selectId) {
  try {
    const subjects = await apiRequest("/subjects/api/list");
    const select = document.getElementById(selectId);

    if (select) {
      select.innerHTML = '<option value="">-- Chọn môn học --</option>';
      subjects.forEach((subject) => {
        const option = document.createElement("option");
        option.value = subject.id;
        option.textContent = `${subject.subject_code} - ${subject.subject_name}`;
        select.appendChild(option);
      });
    }
  } catch (error) {
    showAlert("Lỗi khi tải danh sách môn học", "error");
  }
}

async function loadStudentsByClass(classId, selectId) {
  try {
    const students = await apiRequest(`/students/api/by_class/${classId}`);
    const select = document.getElementById(selectId);

    if (select) {
      select.innerHTML = '<option value="">-- Chọn sinh viên --</option>';
      students.forEach((student) => {
        const option = document.createElement("option");
        option.value = student.id;
        option.textContent = `${student.student_id} - ${student.full_name}`;
        select.appendChild(option);
      });
    }
  } catch (error) {
    showAlert("Lỗi khi tải danh sách sinh viên", "error");
  }
}

// Camera Functions
async function initCamera(videoId) {
  try {
    const video = document.getElementById(videoId);
    cameraStream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 640 },
        height: { ideal: 480 },
        facingMode: "user",
      },
    });
    video.srcObject = cameraStream;
    return true;
  } catch (error) {
    console.error("Error accessing camera:", error);
    showAlert("Không thể truy cập camera. Vui lòng kiểm tra quyền truy cập.", "error");
    return false;
  }
}

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }
}

function captureFrame(videoId, canvasId) {
  const video = document.getElementById(videoId);
  const canvas = document.getElementById(canvasId);

  if (video && canvas) {
    const ctx = canvas.getContext("2d");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    ctx.drawImage(video, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.8);
  }
  return null;
}

// Data Tables Enhancement
function enhanceTable(tableId) {
  const table = document.getElementById(tableId);
  if (table) {
    // Add sorting functionality
    const headers = table.querySelectorAll("th[data-sort]");
    headers.forEach((header) => {
      header.style.cursor = "pointer";
      header.addEventListener("click", () => sortTable(table, header.dataset.sort));
    });

    // Add search functionality
    addTableSearch(table);
  }
}

function sortTable(table, column) {
  const tbody = table.querySelector("tbody");
  const rows = Array.from(tbody.querySelectorAll("tr"));
  const columnIndex = Array.from(table.querySelectorAll("th")).findIndex((th) => th.dataset.sort === column);

  if (columnIndex === -1) return;

  const isNumeric = !isNaN(parseFloat(rows[0]?.cells[columnIndex]?.textContent));

  rows.sort((a, b) => {
    const aVal = a.cells[columnIndex].textContent.trim();
    const bVal = b.cells[columnIndex].textContent.trim();

    if (isNumeric) {
      return parseFloat(aVal) - parseFloat(bVal);
    } else {
      return aVal.localeCompare(bVal, "vi");
    }
  });

  rows.forEach((row) => tbody.appendChild(row));
}

function addTableSearch(table) {
  const searchContainer = table.parentElement;
  const searchInput = document.createElement("input");
  searchInput.type = "text";
  searchInput.className = "form-control mb-3";
  searchInput.placeholder = "Tìm kiếm...";

  searchContainer.insertBefore(searchInput, table);

  searchInput.addEventListener("input", (e) => {
    const searchTerm = e.target.value.toLowerCase();
    const rows = table.querySelectorAll("tbody tr");

    rows.forEach((row) => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(searchTerm) ? "" : "none";
    });
  });
}

// Local Storage Functions
function saveToStorage(key, data) {
  try {
    localStorage.setItem(key, JSON.stringify(data));
  } catch (error) {
    console.error("Error saving to localStorage:", error);
  }
}

function loadFromStorage(key) {
  try {
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : null;
  } catch (error) {
    console.error("Error loading from localStorage:", error);
    return null;
  }
}

// Export Functions
function exportToCSV(tableId, filename) {
  const table = document.getElementById(tableId);
  if (!table) return;

  const rows = table.querySelectorAll("tr");
  const csvContent = Array.from(rows)
    .map((row) => {
      const cells = row.querySelectorAll("th, td");
      return Array.from(cells)
        .map((cell) => `"${cell.textContent.trim()}"`)
        .join(",");
    })
    .join("\n");

  downloadFile(csvContent, filename + ".csv", "text/csv");
}

function downloadFile(content, filename, contentType) {
  const blob = new Blob([content], { type: contentType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// Animation Functions
function fadeIn(element, duration = 300) {
  element.style.opacity = "0";
  element.style.display = "block";

  let start = performance.now();

  function animate(currentTime) {
    const elapsed = currentTime - start;
    const progress = Math.min(elapsed / duration, 1);

    element.style.opacity = progress;

    if (progress < 1) {
      requestAnimationFrame(animate);
    }
  }

  requestAnimationFrame(animate);
}

function slideDown(element, duration = 300) {
  element.style.height = "0";
  element.style.overflow = "hidden";
  element.style.display = "block";

  const targetHeight = element.scrollHeight;
  let start = performance.now();

  function animate(currentTime) {
    const elapsed = currentTime - start;
    const progress = Math.min(elapsed / duration, 1);

    element.style.height = targetHeight * progress + "px";

    if (progress === 1) {
      element.style.height = "auto";
      element.style.overflow = "visible";
    } else {
      requestAnimationFrame(animate);
    }
  }

  requestAnimationFrame(animate);
}

// Initialize functions when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  // Initialize tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });

  // Initialize popovers
  const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
  popoverTriggerList.map(function (popoverTriggerEl) {
    return new bootstrap.Popover(popoverTriggerEl);
  });

  // Add form validation to all forms
  const forms = document.querySelectorAll("form[data-validate]");
  forms.forEach((form) => {
    form.addEventListener("submit", function (e) {
      if (!validateForm(form.id)) {
        e.preventDefault();
        showAlert("Vui lòng điền đầy đủ thông tin bắt buộc", "warning");
      }
    });
  });

  // Auto-hide alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert:not(.alert-permanent)");
  alerts.forEach((alert) => {
    setTimeout(() => {
      if (alert.parentNode) {
        alert.remove();
      }
    }, 5000);
  });

  // Enhance tables with sorting and search
  const tables = document.querySelectorAll("table[data-enhance]");
  tables.forEach((table) => enhanceTable(table.id));
});

// Cleanup on page unload
window.addEventListener("beforeunload", function () {
  stopCamera();
});

// Export functions for global access
window.FaceAttendance = {
  showAlert,
  validateForm,
  apiRequest,
  loadClasses,
  loadSubjects,
  loadStudentsByClass,
  initCamera,
  stopCamera,
  captureFrame,
  exportToCSV,
  saveToStorage,
  loadFromStorage,
};
