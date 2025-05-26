import "./FormWrapper.css";
import Button from "../Button/Button";
import React, { useState, useEffect } from "react";

function FormWrapper({
  fields = [],
  onSubmit,
  renderButtons,
  defaultValues = {},
}) {
  const [formData, setFormData] = useState(defaultValues);
  useEffect(() => {
    setFormData(defaultValues);
  }, [defaultValues]);

  const handleChange = (name, value) => {
    setFormData((prev) => {
      const updated = { ...prev, [name]: value };
      console.log(`Updated field: ${name} =`, value);
      console.log("Current formData:", updated);
      return updated;
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log("Attempting to submit with formData:", formData);

    const missingFields = fields.filter((field) => {
      const value = formData[field.name];
      if (field.type === "checkbox-group") return !value || value.length === 0;
      return value === undefined || value === "";
    });

    if (missingFields.length > 0) {
      console.warn(
        "Missing required fields:",
        missingFields.map((f) => f.name)
      );
      alert("Vui lòng điền đầy đủ thông tin trước khi tiếp tục.");
      return;
    }

    for (const field of fields) {
      const value = formData[field.name];

      if (field.name === "fullName") {
        const nameIsValid = /^[\p{L}\s'‑-]+$/u.test(value.trim());
        if (!nameIsValid) {
          alert("Tên không được chứa số hoặc ký tự đặc biệt.");
          return;
        }
      }

      if (field.name === "phone") {
        const phoneIsValid = /^\d{10}$/.test(value);
        if (!phoneIsValid) {
          alert("Số điện thoại phải gồm đúng 10 chữ số (0‑9).");
          return;
        }
      }

      if (field.name === "birthDate") {
        const inputDate = new Date(value);
        const today = new Date();
        inputDate.setHours(0, 0, 0, 0);
        today.setHours(0, 0, 0, 0);

        if (isNaN(inputDate) || inputDate > today) {
          alert("Ngày sinh không được lớn hơn ngày hiện tại.");
          return;
        }

        let months =
          (today.getFullYear() - inputDate.getFullYear()) * 12 +
          (today.getMonth() - inputDate.getMonth());
        if (today.getDate() < inputDate.getDate()) months--;

        if (months < 2 || months > 54) {
          alert("Chỉ hỗ trợ trẻ từ 2 tháng đến 4,5 tuổi (54 tháng).");
          return;
        }
      }

      if (field.name === "birthDatePredict") {
        const inputDate = new Date(value);
        const today = new Date();
        inputDate.setHours(0, 0, 0, 0);
        today.setHours(0, 0, 0, 0);

        if (isNaN(inputDate) || inputDate > today) {
          alert("Ngày sinh không được lớn hơn ngày hiện tại.");
          return;
        }

        const years = today.getFullYear() - inputDate.getFullYear();
        const months =
          years * 12 +
          today.getMonth() -
          inputDate.getMonth() -
          (today.getDate() < inputDate.getDate() ? 1 : 0);

        if (months < 0 || months > 96) {
          alert("Chỉ hỗ trợ trẻ dưới 8 tuổi (96 tháng).");
          return;
        }
      }
    }

    console.log("Form passed validation. Submitting...");
    onSubmit(formData);
  };

  const todayISO = new Date().toISOString().split("T")[0];

  const renderField = (field) => {
    switch (field.type) {
      case "text":
      case "file":
        return (
          <input
            type={field.type}
            name={field.name}
            placeholder={field.placeholder || ""}
            value={
              field.type !== "file" ? formData?.[field.name] ?? "" : undefined
            }
            onChange={(e) => {
              const value =
                field.type === "file" ? e.target.files[0] : e.target.value;
              handleChange(field.name, value);
              if (field.onChange) field.onChange(field.name, value);
            }}
          />
        );

      case "date":
        return (
          <input
            type="date"
            name={field.name}
            value={formData[field.name] || ""}
            max={todayISO}
            min="1950-01-01"
            onChange={(e) => {
              handleChange(field.name, e.target.value);
              field.onChange?.(field.name, e.target.value);
            }}
            onInvalid={(e) =>
              e.target.setCustomValidity(
                "Ngày không được lớn hơn ngày hiện tại."
              )
            }
            onInput={(e) => e.target.setCustomValidity("")}
          />
        );

      case "select":
        return (
          <select
            name={field.name}
            value={formData[field.name] || ""}
            onChange={(e) => {
              handleChange(field.name, e.target.value);
              field.onChange?.(field.name, e.target.value);
            }}
          >
            <option value="">-- Chọn --</option>
            {field.options.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        );

      case "radio":
        return (
          <div className="radio-group">
            {field.options.map((opt) => (
              <label key={opt}>
                <input
                  type="radio"
                  name={field.name}
                  value={opt}
                  checked={formData[field.name] === opt}
                  onChange={(e) => {
                    handleChange(field.name, e.target.value);
                    if (field.onChange)
                      field.onChange(field.name, e.target.value);
                  }}
                />{" "}
                {opt}
              </label>
            ))}
          </div>
        );

      case "checkbox-group":
        return (
          <div className="checkbox-group">
            {field.options.map((opt) => (
              <label key={opt}>
                <input
                  type="checkbox"
                  name={field.name}
                  checked={formData[field.name]?.includes(opt) || false}
                  onChange={(e) => {
                    const selected = new Set(formData[field.name] || []);
                    e.target.checked ? selected.add(opt) : selected.delete(opt);
                    const updated = [...selected];
                    handleChange(field.name, updated);
                    if (field.onChange) field.onChange(field.name, updated);
                  }}
                />{" "}
                {opt}
              </label>
            ))}
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <form className="form-wrapper" onSubmit={handleSubmit}>
      {fields.map((field) => (
        <div className="form-field" key={field.name}>

          <label className="text-lable">{field.label}</label>
          <div className="field-input-container">
            {renderField(field)}
            {field.note && <div className="field-note">{field.note}</div>}
          </div>
        </div>
      ))}

      {renderButtons ? (
        renderButtons({ onSubmit: handleSubmit })
      ) : (
        <div className="form-button-wrapper">
          <Button className="button-next" type="submit">
            TIẾP TỤC
          </Button>
        </div>
      )}
    </form>
  );
}

export default FormWrapper;
