import React from "react";
import FormWrapper from "./FormWrapper";
import Button from "../Button/Button";
import "./FormParentInfo.css";

function FormParentInfo({ onSubmit, onBack, defaultValues = {}, onChange }) {
  /* ───────── 1. Cấu hình field ───────── */
  const fields = [
    {
      type: "text",
      name: "parentName",
      label: "Họ và tên:",
      onChange,
      inputProps: { required: true },
    },
    {
      type: "text",
      name: "birthYear",
      label: "Năm sinh:",
      inputProps: {
        pattern: "\\d{4}",
        title: "Nhập năm gồm 4 chữ số (≥ 1950)",
        required: true,
        inputMode: "numeric",
      },
      onChange,
    },
    {
      type: "radio",
      name: "parentGender",
      label: "Giới tính:",
      options: ["Nam", "Nữ"],
      onChange,
      inputProps: { required: true },
    },
    {
      type: "select",
      name: "relationship",
      label: "Mối quan hệ với trẻ:",
      options: ["Ba / Mẹ", "Người thân khác"],
      onChange,
      inputProps: { required: true },
    },
    {
      type: "text",
      name: "address",
      label: "Địa chỉ chi tiết:",
      onChange,
      inputProps: { required: true },
    },
    {
      type: "text",
      name: "phone",
      label: "Số điện thoại:",
      inputProps: {
        title: "Nhập đúng 10 chữ số",
        inputMode: "numeric",
        required: true,
      },
      onChange,
    },
    {
      type: "radio",
      name: "place",
      label: "Nơi làm sàng lọc:",
      options: ["Nhà", "Phòng khám", "Khác"],
      onChange,
      inputProps: { required: true },
    },
  ];

  /* ───────── 2. Hàm validate riêng ───────── */
  const validateParentInfo = (data) => {
    // 1) Họ tên
    if (!/^[\p{L}\s'‑-]+$/u.test((data.parentName || "").trim())) {
      return "Tên không được chứa số hoặc ký tự đặc biệt.";
    }

    // 2) Năm sinh
    const year = parseInt(data.birthYear, 10);
    if (isNaN(year) || year < 1950) {
      return "Năm sinh phải ≥ 1950 và gồm 4 chữ số.";
    }

    // 3) Số điện thoại 10 số
    if (!/^\d{10}$/.test(data.phone || "")) {
      return "Số điện thoại phải gồm đúng 10 chữ số.";
    }

    // 4) Các trường radio/select đã đánh required,
    //    nhưng kiểm tra lại để chắc chắn (phòng bypass HTML)
    if (!data.parentGender) return "Vui lòng chọn giới tính.";
    if (!data.relationship) return "Vui lòng chọn mối quan hệ với trẻ.";
    if (!data.place) return "Vui lòng chọn nơi làm sàng lọc.";

    // 5) Địa chỉ không rỗng
    if (!data.address?.trim()) return "Vui lòng nhập địa chỉ chi tiết.";

    return null; // ✔️ hợp lệ
  };

  /* ───────── 3. handleSubmit cục bộ ───────── */
  const handleSubmitLocal = (formData) => {
    const err = validateParentInfo(formData);
    if (err) {
      alert(err);
      return;
    }
    onSubmit(formData); // truyền ra ngoài khi OK
  };

  /* ───────── 4. Render ───────── */
  return (
    <FormWrapper
      fields={fields}
      defaultValues={defaultValues}
      onSubmit={handleSubmitLocal}      
      renderButtons={({ onSubmit }) => (
        <div className="form-button-wrapper">
          <Button type="button" onClick={onBack}>
            QUAY LẠI
          </Button>
          <Button type="submit" onClick={onSubmit}>
            XEM KẾT QUẢ
          </Button>
        </div>
      )}
    />
  );
}

export default FormParentInfo;
