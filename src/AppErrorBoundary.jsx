import { Component } from "react";
import { Alert, Button, Container } from "react-bootstrap";

export default class AppErrorBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(error, info) {
    console.error("Unexpected interface error", error, info);
  }

  render() {
    if (this.state.failed) {
      return (
        <Container className="page-wrap">
          <Alert variant="danger" role="alert">
            <Alert.Heading>Something went wrong</Alert.Heading>
            <p>We couldn’t display this page. Your saved information has not been changed.</p>
            <Button variant="outline-danger" onClick={() => window.location.reload()}>Reload page</Button>
          </Alert>
        </Container>
      );
    }
    return this.props.children;
  }
}
