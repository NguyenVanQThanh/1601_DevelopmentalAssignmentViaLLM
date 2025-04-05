import React from 'react';
import './FormWrapper.css';
import Button from '../Button/Button';

function FormWrapper({ fields = [], onSubmit }) {
  const [formData, setFormData] = React.useState({});

  const handleChange = (name, value) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
  
    const missingFields = fields.filter((field) => {
      const value = formData[field.name];
      if (field.type === 'checkbox-group') {
        return !value || value.length === 0;
      }
      return value === undefined || value === '';
    });
  
    if (missingFields.length > 0) {
      alert('Vui lòng điền đầy đủ thông tin trước khi tiếp tục.');
      return;
    }
  
    onSubmit(formData);
  };

  const renderField = (field) => {
    switch (field.type) {
      case 'text':
      case 'date':
      case 'file':
        return (
          <input 
            type={field.type}
            name={field.name}
            placeholder={field.placeholder || ''}
            value={field.type !== 'file' ? formData[field.name] || '' : undefined}
            onChange={(e) =>
              handleChange(
                field.name,
                field.type === 'file' ? e.target.files[0] : e.target.value
              )
            }
          />
        );

      case 'select':
        return (
          <select
            name={field.name}
            value={formData[field.name] || ''}
            onChange={(e) => handleChange(field.name, e.target.value)}
          >
            <option value="">-- Chọn --</option>
            {field.options.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        );

        case 'radio':
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
                        if (field.onChange) field.onChange(e.target.value); // ✅ gọi callback nếu có
                      }}
                    />{' '}
                    {opt}
                  </label>
                ))}
              </div>
            );

      case 'checkbox-group':
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
                    handleChange(field.name, [...selected]);
                  }}
                />{' '}
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
          <label className='text-lable'>{field.label}</label>
          {renderField(field)}
        </div>
      ))}

      {/* ✅ Button tách riêng, căng giữa toàn form */}
      <div className="form-button-wrapper">
        <Button type="submit">TIẾP TỤC</Button>
      </div>
    </form>
  );
}

export default FormWrapper;
