import React from "react";
import FormWrapper from "./FormWrapper";
import Button from "../Button/Button";
import "./FormParentInfo.css";

function FormParentInfo({ onSubmit, onBack, defaultValues = {}, onChange }) {
  const fields = [
    { type: "text", name: "parentName", label: "Họ và tên:", onChange },
    {
      type: "text",
      name: "birthYear",
      label: "Năm sinh:",
      inputProps: {
        pattern: "\\d{4}",
        title: "Nhập năm gồm 4 chữ số",
        inputMode: "numeric"
      },
      onChange
    },
    {
      type: "radio",
      name: "parentGender",
      label: "Giới tính:",
      options: ["Nam", "Nữ"],
      onChange
    },
    {
      type: "select",
      name: "relationship",
      label: "Mối quan hệ với trẻ:",
      options: ["Ba / Mẹ", "Người thân khác"],
      onChange
    },
    { type: "text", name: "address", label: "Địa chỉ chi tiết:", onChange },
    {
      type: "text",
      name: "phone",
      label: "Số điện thoại:",
      inputProps: {
        pattern: "[0-9]+",
        title: "Chỉ được nhập số",
        inputMode: "numeric"
      },
      onChange
    },
    {
      type: "radio",
      name: "place",
      label: "Nơi làm sàng lọc:",
      options: ["Nhà", "Phòng khám", "Khác"],
      onChange
    },
  ];

  return (
    <FormWrapper
      fields={fields}
      defaultValues={defaultValues}
      onSubmit={onSubmit}
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
