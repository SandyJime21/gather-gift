import { Form } from 'react-bootstrap';
export default function WishAudiencePicker({value,onChange}) {
 return <Form.Group controlId="wish-audience-scope" className="mb-3"><Form.Label>Audience</Form.Label><Form.Select value={value} onChange={event=>onChange(event.target.value)}><option value="custom">Selected invited family accounts</option><option value="private">Private - this shared login only</option><option value="family">Family accounts</option><option value="followers">Families following me</option><option value="public">Public - anyone</option></Form.Select></Form.Group>;
}
