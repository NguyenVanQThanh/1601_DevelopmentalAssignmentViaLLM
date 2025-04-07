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
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();

    // ✅ Kiểm tra các trường bắt buộc
    const missingFields = fields.filter((field) => {
      const value = formData[field.name];
      if (field.type === "checkbox-group") {
        return !value || value.length === 0;
      }
      return value === undefined || value === "";
    });

    if (missingFields.length > 0) {
      alert("Vui lòng điền đầy đủ thông tin trước khi tiếp tục.");
      return;
    }

    // ✅ Duyệt fields đang hiển thị để kiểm tra validate động
    for (const field of fields) {
      const value = formData[field.name];

      if (field.name === "phone") {
        const phoneIsValid = /^[0-9]+$/.test(value);
        if (!phoneIsValid) {
          alert("Số điện thoại chỉ được chứa chữ số (0-9).");
          return;
        }
      }

      if (field.name === "birthYear") {
        const yearIsValid = /^\d{4}$/.test(value) && parseInt(value, 10) > 1950;
        if (!yearIsValid) {
          alert("Năm sinh không hợp lệ.");
          return;
        }
      }
    }

    onSubmit(formData);
  };

  const renderField = (field) => {
    switch (field.type) {
      case "text":
      case "date":
      case "file":
        return (
          
          <input
            type={field.type}
            name={field.name}
            placeholder={field.placeholder || ""}
            value={
              field.type !== "file" ? formData[field.name] || "" : undefined
            }
            onChange={(e) => {
              const value =
                field.type === "file" ? e.target.files[0] : e.target.value;
              handleChange(field.name, value);
              if (field.onChange) field.onChange(field.name, value); 
            }}
          />
        );

      case "select":
        return (
          <select
            name={field.name}
            value={formData[field.name] || ""}
            onChange={(e) => {
              handleChange(field.name, e.target.value);
              if (field.onChange) field.onChange(field.name, e.target.value);
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
                    if (field.onChange) field.onChange(field.name, updated); // 👈 THÊM
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
          {renderField(field)}
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
