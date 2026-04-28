/**
 * Converts an array of objects to CSV format and triggers a download
 * @param {Array} data - Array of objects to convert to CSV
 * @param {string} filename - Name of the file to download
 */
export function downloadCSV(data, filename) {
  if (!data || data.length === 0) return;

  // Get headers from the first object
  const headers = Object.keys(data[0]);
  
  const escapeCsvValue = (value) => {
    if (value === null || value === undefined) return '';
    const str = String(value);
    if (str.includes(',') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };

  const csvContent = [
    headers.map(escapeCsvValue).join(','),
    ...data.map(row =>
      headers.map(header => escapeCsvValue(row[header])).join(',')
    )
  ].join('\n');

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}.csv`);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
} 