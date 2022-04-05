import React, { useEffect } from "react";
import { useRecoilValue, useResetRecoilState } from "recoil";
import styled from "styled-components";

import SamplesContainer from "./SamplesContainer";
import HorizontalNav from "../components/HorizontalNav";
import SampleModal from "./SampleModal";
import * as selectors from "../recoil/selectors";
import { useGA } from "../utils/hooks";
import Loading from "../components/Loading";
import * as schemaAtoms from "../recoil/schema";
import { modal } from "../recoil/atoms";

const PLOTS = ["Sample tags", "Label tags", "Labels", "Other fields"];

const Container = styled.div`
  height: 100%;
  display: flex;
  flex-direction: column;
`;

const Body = styled.div`
  width: 100%;
  flex-grow: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
`;

const useResetPaths = () => {
  const dataset = useRecoilValue(selectors.datasetName);
  const resetPaths = useResetRecoilState(
    schemaAtoms.activeFields({ modal: false })
  );
  useEffect(() => {
    resetPaths();
  }, [dataset]);
};

function Dataset() {
  const isModalActive = Boolean(useRecoilValue(modal));
  const hasDataset = useRecoilValue(selectors.hasDataset);

  useGA();
  useResetPaths();

  useEffect(() => {
    document.body.classList.toggle("noscroll", isModalActive);
    document
      .getElementById("modal")
      ?.classList.toggle("modalon", isModalActive);
  }, [isModalActive]);
  const datasets = useRecoilValue(selectors.datasets);

  return (
    <>
      {isModalActive && <SampleModal />}
      <Container key={1}>
        {hasDataset ? (
          <>
            <HorizontalNav entries={PLOTS} key={"nav"} />
            <Body key={"body"}>
              <SamplesContainer key={"samples"} />
            </Body>
          </>
        ) : (
          <Loading
            text={datasets.length ? "No dataset selected" : "No datasets"}
            key={2}
          />
        )}
      </Container>
    </>
  );
}

export default React.memo(Dataset);