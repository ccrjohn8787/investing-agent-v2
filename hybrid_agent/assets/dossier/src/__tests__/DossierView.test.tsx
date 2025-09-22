import { fireEvent, render, screen } from '@testing-library/react';
import DossierView from '../components/DossierView';
import { completePayload, missingSectionsPayload } from './fixtures';

describe('DossierView', () => {
  it('renders Stage-0 rows and Reverse DCF summary', () => {
    render(<DossierView analyst={completePayload.analyst} verifier={completePayload.verifier} />);

    expect(screen.getByText('Circle of Competence')).toBeInTheDocument();
    expect(screen.getByText('ROIC exceeds WACC')).toBeInTheDocument();
    expect(screen.getByText(/QA PASS/i)).toBeInTheDocument();
    expect(screen.getAllByText(/WACC/).length).toBeGreaterThan(0);
    expect(screen.getByText(/9.0% \(8.0% – 10.0%\)/)).toBeInTheDocument();
    expect(screen.getByText(/Scenario set derived/)).toBeInTheDocument();
    expect(screen.getByText(/IRR: 14.5%/i)).toBeInTheDocument();
    expect(screen.getByText('Delta Highlights')).toBeInTheDocument();
    expect(screen.getByText('Trigger Monitor')).toBeInTheDocument();
  });

  it('shows NA placeholders and QA blocker reasons when data is missing', () => {
    render(<DossierView analyst={missingSectionsPayload.analyst} verifier={missingSectionsPayload.verifier} />);

    expect(screen.getByText(/QA BLOCKER/i)).toBeInTheDocument();
    expect(screen.getByText('Missing Valuation gate')).toBeInTheDocument();
    expect(screen.getAllByText('NA').length).toBeGreaterThan(0);
    expect(screen.getByText('No active triggers.')).toBeInTheDocument();
  });

  it('toggles provenance table', () => {
    render(<DossierView analyst={completePayload.analyst} verifier={completePayload.verifier} />);
    const toggle = screen.getByRole('button', { name: /show details/i });
    fireEvent.click(toggle);
    expect(screen.getByText(/MACRO-UBER-VALUATION-2024/)).toBeInTheDocument();
  });
});
