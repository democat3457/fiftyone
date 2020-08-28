import React, { useState, useEffect, useRef } from "react";
import { useRecoilState, useRecoilValue, useSetRecoilState } from "recoil";
import styled from "styled-components";

import { Grid, Sticky } from "semantic-ui-react";

import DisplayOptionsSidebar from "../components/DisplayOptionsSidebar";
import ImageContainerHeader from "../components/ImageContainerHeader";
import Samples from "../components/Samples";
import ViewBar from "../components/ViewBar/ViewBar";
import { VerticalSpacer } from "../components/utils";

import * as atoms from "../recoil/atoms";
import * as selectors from "../recoil/selectors";
import { useResizeHandler, useScrollHandler } from "../utils/hooks";
import { VALID_LABEL_TYPES, VALID_SCALAR_TYPES } from "../utils/labels";

const Root = styled.div`
  .ui.grid > .sidebar-column {
    flex: 0 0 17rem;
    z-index: 400;
    margin-right: -0.5em;
  }

  .ui.grid > .content-column {
    flex: 1;
  }
`;

const DisplayOptionsWrapper = (props) => {
  const { containerRef, sidebarRef, stickyHeaderRef, displayProps } = props;
  const {
    activeTags,
    activeLabels,
    activeOther,
    setActiveTags,
    setActiveLabels,
    setActiveOther,
  } = displayProps;
  const labelSampleCounts = useRecoilValue(selectors.labelSampleCounts);
  const colorMapping = useRecoilValue(selectors.labelColorMapping);
  const tagNames = useRecoilValue(selectors.tagNames);
  const tagSampleCounts = useRecoilValue(selectors.tagSampleCounts);
  const filters = useRecoilValue(selectors.labelFilters);
  const setModalFilters = useSetRecoilState(selectors.modalLabelFilters);
  const [sidebarHeight, setSidebarHeight] = useState("unset");
  const fieldSchema = useRecoilValue(selectors.fieldSchema);
  const labelNames = useRecoilValue(selectors.labelNames);
  const labelTypes = useRecoilValue(selectors.labelTypes);

  useEffect(() => {
    setModalFilters(filters);
  }, [filters]);
  let headerHeight = 0;

  const getDisplayOptions = (values, counts, selected) => {
    return [...values].sort().map(({ name, type }) => ({
      name,
      type,
      count: counts[name],
      selected: Boolean(selected[name]),
    }));
  };
  const handleSetDisplayOption = (selected, setSelected) => (entry) => {
    setSelected((selected) => ({
      ...selected,
      [entry.name]: entry.selected,
    }));
  };
  if (stickyHeaderRef.current && stickyHeaderRef.current.stickyRect) {
    headerHeight = stickyHeaderRef.current.stickyRect.height;
  }
  const updateSidebarHeight = () => {
    if (sidebarRef.current) {
      setSidebarHeight(
        window.innerHeight - sidebarRef.current.getBoundingClientRect().top
      );
    }
  };
  useResizeHandler(updateSidebarHeight, [sidebarRef.current]);
  useScrollHandler(updateSidebarHeight, [sidebarRef.current]);
  useEffect(updateSidebarHeight, []);
  const labelNameGroups = {
    labels: [],
    scalars: [],
    unsupported: [],
  };
  for (const name of labelNames) {
    if (VALID_LABEL_TYPES.includes(labelTypes[name])) {
      labelNameGroups.labels.push({ name, type: labelTypes[name] });
    } else if (VALID_SCALAR_TYPES.includes(fieldSchema[name])) {
      labelNameGroups.scalars.push({ name });
    } else {
      labelNameGroups.unsupported.push({ name });
    }
  }

  return (
    <Grid.Column className="sidebar-column">
      <Sticky
        context={containerRef}
        offset={headerHeight}
        style={{ height: "100%" }}
        styleElement={{ height: "100%" }}
      >
        <DisplayOptionsSidebar
          colorMapping={colorMapping}
          tags={getDisplayOptions(
            tagNames.map((t) => ({ name: t })),
            tagSampleCounts,
            activeTags
          )}
          labels={getDisplayOptions(
            labelNameGroups.labels,
            labelSampleCounts,
            activeLabels
          )}
          onSelectTag={handleSetDisplayOption(activeTags, setActiveTags)}
          onSelectLabel={handleSetDisplayOption(activeLabels, setActiveLabels)}
          scalars={getDisplayOptions(
            labelNameGroups.scalars,
            labelSampleCounts,
            activeOther
          )}
          onSelectScalar={handleSetDisplayOption(activeOther, setActiveOther)}
          unsupported={getDisplayOptions(
            labelNameGroups.unsupported,
            labelSampleCounts,
            activeLabels
          )}
          style={{
            maxHeight: sidebarHeight,
            overflowY: "auto",
            overflowX: "hidden",
            paddingRight: 25,
            marginRight: -25,
            scrollbarWidth: "thin",
          }}
          ref={sidebarRef}
        />
      </Sticky>
    </Grid.Column>
  );
};

const SamplesContainer = (props) => {
  const [showSidebar, setShowSidebar] = useRecoilState(atoms.sidebarVisible);
  const datasetName = useRecoilValue(selectors.datasetName);
  const numSamples = useRecoilValue(selectors.numSamples);

  const containerRef = useRef();
  const stickyHeaderRef = useRef();
  const sidebarRef = useRef();

  return (
    <Root ref={containerRef} showSidebar={showSidebar}>
      <VerticalSpacer opaque height={5} />
      <Sticky ref={stickyHeaderRef} context={containerRef}>
        <ViewBar />
        <VerticalSpacer opaque height={5} />
        <ImageContainerHeader
          datasetName={datasetName}
          total={numSamples}
          showSidebar={showSidebar}
          onShowSidebar={setShowSidebar}
        />
        <VerticalSpacer opaque height={5} />
      </Sticky>
      <Grid>
        {showSidebar ? (
          <DisplayOptionsWrapper
            sidebarRef={sidebarRef}
            stickyHeaderRef={stickyHeaderRef}
            containerRef={containerRef}
            {...props}
          />
        ) : null}
        <Grid.Column className="content-column">
          <Samples {...props} />
        </Grid.Column>
      </Grid>
    </Root>
  );
};

export default SamplesContainer;
